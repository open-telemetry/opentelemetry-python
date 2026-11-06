# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
#
"""Serialization of baggage into the W3C ``baggage`` HTTP header.

:class:`W3CBaggagePropagator` writes the baggage held in a context into the
``baggage`` header when a request is sent, and reads it back out when one is
received, following https://www.w3.org/TR/baggage/.

The format caps the size of the header, of each list-member, and the number of
list-members. Nothing here raises, so oversized baggage degrades the telemetry
instead of the request. Which entries go is not uniform: an entry that holds a
non-ASCII character, fails validation or exceeds the per-entry limit is dropped
on its own with a warning, while exceeding the entry count or the total header
length stops processing there and discards every remaining entry, including
entries that would have fitted.
"""

from collections.abc import Iterable, Iterator, Mapping
from logging import getLogger
from urllib.parse import quote, unquote

from opentelemetry.baggage import (
    _is_valid_key,
    _is_valid_pair,
    get_all,
    set_baggage,
)
from opentelemetry.context import get_current
from opentelemetry.context.context import Context
from opentelemetry.propagators import textmap

_logger = getLogger(__name__)


def _filter_valid_entries(
    entries: Iterable[str],
    max_pair_length: int,
) -> Iterator[str]:
    """Drop the baggage entries that cannot appear in a header.

    An empty entry is skipped silently. An entry holding a non-ASCII character
    or exceeding ``max_pair_length`` is skipped with a warning naming its key.

    Args:
        entries: The candidate entries, each one a ``key=value`` string.
        max_pair_length: Maximum length of a single entry, in characters.

    Yields:
        Each entry that passes every check, in the order received.
    """
    for entry in entries:
        if not entry:
            continue
        if not entry.isascii():
            _logger.warning(
                "Baggage entry with key `%s` contains non-ASCII characters",
                entry.split("=", 1)[0],
            )
            continue
        if len(entry) > max_pair_length:
            _logger.warning(
                "Baggage entry with key `%s` exceeded the maximum number of bytes per list-member with length %d",
                entry.split("=", 1)[0],
                len(entry),
            )
            continue
        yield entry


def _apply_baggage_limits(
    entries: Iterable[str],
    max_pairs: int,
    max_pair_length: int,
    max_header_length: int,
) -> Iterator[str]:
    """Apply W3C Baggage size limits to a sequence of baggage entries.

    Yields entries that fit within the W3C specification limits.
    Logs warnings when entries are dropped.

    Iteration stops at the first entry that would exceed ``max_pairs`` or
    ``max_header_length``, so every later entry is dropped as well even if it
    would have fitted on its own.

    Args:
        entries: The candidate entries, each one a ``key=value`` string.
        max_pairs: Maximum number of entries to yield.
        max_pair_length: Maximum length of a single entry, in characters.
        max_header_length: Maximum combined length of the entries, counting
            the comma that joins them.

    Yields:
        Each entry that fits within every limit, in the order received.
    """
    length = 0
    for index, entry in enumerate(_filter_valid_entries(entries, max_pair_length)):
        if index >= max_pairs:
            _logger.warning("Baggage exceeded the maximum number of list-members")
            return

        length += (1 if index > 0 else 0) + len(entry)
        if length > max_header_length:
            _logger.warning("Baggage exceeded the maximum number of bytes per baggage-string")
            return
        yield entry


class W3CBaggagePropagator(textmap.TextMapPropagator):
    """Extracts and injects Baggage which is used to annotate telemetry."""

    _MAX_HEADER_LENGTH = 8192
    _MAX_PAIR_LENGTH = 4096
    _MAX_PAIRS = 180
    _BAGGAGE_HEADER_NAME = "baggage"

    def extract(
        self,
        carrier: textmap.CarrierT,
        context: Context | None = None,
        getter: textmap.Getter[textmap.CarrierT] = textmap.default_getter,
    ) -> Context:
        """Extract Baggage from the carrier.

        See
        `opentelemetry.propagators.textmap.TextMapPropagator.extract`

        A list-member that does not parse, that fails validation, that
        holds a non-ASCII character or that is longer than the per-entry
        limit is skipped on its own, so the rest of the header still
        extracts. Exceeding the entry count or the total header length is
        different: extraction stops there and every remaining entry is
        discarded, including entries that would have fitted.

        Args:
            carrier: The object holding the incoming headers, for example the
                header mapping of an HTTP request.
            context: The context to add the extracted baggage to. If ``None``,
                the current context is used.
            getter: Reads the ``baggage`` header values out of ``carrier``.

        Returns:
            A new context holding the baggage found in ``carrier``. When the
            header is absent or empty, the context is returned unchanged.
        """

        if context is None:
            context = get_current()

        headers = getter.get(carrier, self._BAGGAGE_HEADER_NAME)

        if not headers:
            return context

        for entry in _apply_baggage_limits(
            _split_baggage_entries(headers),
            max_pairs=self._MAX_PAIRS,
            max_pair_length=self._MAX_PAIR_LENGTH,
            max_header_length=self._MAX_HEADER_LENGTH,
        ):
            try:
                name, value = entry.split("=", 1)
            except Exception:  # pylint: disable=broad-exception-caught
                _logger.warning("Baggage list-member `%s` doesn't match the format", entry)
                continue

            # W3C Baggage allows optional whitespace around "="
            name = name.strip(" \t")
            value = value.strip(" \t")

            if not _is_valid_pair(name, value):
                _logger.warning("Invalid baggage entry: `%s`", entry)
                continue

            # Properties are validated but not stored, as the API has no metadata support
            value = value.split(";", 1)[0].rstrip(" \t")

            context = set_baggage(
                name,
                unquote(value),
                context=context,
            )

        return context

    def inject(
        self,
        carrier: textmap.CarrierT,
        context: Context | None = None,
        setter: textmap.Setter[textmap.CarrierT] = textmap.default_setter,
    ) -> None:
        """Injects Baggage into the carrier.

        See
        `opentelemetry.propagators.textmap.TextMapPropagator.inject`

        Nothing is written when the context holds no baggage, and nothing is
        written when every entry was dropped, whether for carrying a key that
        is not a valid baggage token or for breaking a size limit.

        Args:
            carrier: The object to write the outgoing header into, for example
                the header mapping of an outbound HTTP request.
            context: The context to read the baggage from. If ``None``, the
                current context is used.
            setter: Writes the ``baggage`` header into ``carrier``.
        """
        baggage_entries = get_all(context=context)
        if not baggage_entries:
            return

        baggage_string = ",".join(
            _apply_baggage_limits(
                _encode_baggage_pairs(baggage_entries),
                max_pairs=self._MAX_PAIRS,
                max_pair_length=self._MAX_PAIR_LENGTH,
                max_header_length=self._MAX_HEADER_LENGTH,
            )
        )

        if baggage_string:
            setter.set(carrier, self._BAGGAGE_HEADER_NAME, baggage_string)

    @property
    def fields(self) -> set[str]:
        """Returns a set with the fields set in `inject`.

        Returns:
            A set holding the single name ``"baggage"``. A caller clearing a
            carrier before injecting into it should remove these names.
        """
        return {self._BAGGAGE_HEADER_NAME}


def _split_baggage_entries(headers: Iterable[str]) -> Iterator[str]:
    """Yield the list-members of all baggage headers, combined as a single baggage string.

    Several ``baggage`` headers on one message are treated as one list, which
    is what the header format requires. Surrounding whitespace is stripped
    from each list-member.

    Args:
        headers: The raw values of every ``baggage`` header received.

    Yields:
        Each comma-separated list-member, stripped of surrounding whitespace.
        An empty header yields one empty string, which the caller filters out.
    """
    for header in headers:
        start = 0
        while True:
            end = header.find(",", start)
            if end == -1:
                yield header[start:].strip(" \t")
                break
            yield header[start:end].strip(" \t")
            start = end + 1


def _encode_baggage_pairs(
    baggage_entries: Mapping[str, object],
) -> Iterator[str]:
    """Yield 'key=value' pairs with percent-encoded values from baggage entries.

    A pair whose key is not a valid baggage name is skipped with a warning.
    Values are percent-encoded, so a value containing a comma, a semicolon or
    an equals sign survives the round trip.

    Args:
        baggage_entries: The baggage held in a context, as returned by
            :func:`opentelemetry.baggage.get_all`. Each value is converted
            with :func:`str` before being encoded.

    Yields:
        One ``key=value`` string per valid entry, with the value
        percent-encoded.
    """
    for key, value in baggage_entries.items():
        if not _is_valid_key(key):
            _logger.warning("Baggage key `%s` is not a valid token", key)
            continue
        yield str(key) + "=" + quote(str(value), safe="")
