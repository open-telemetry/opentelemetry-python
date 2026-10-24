# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
#
from collections.abc import Iterable, Iterator, Mapping
from logging import getLogger
from typing import Any
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
        """Returns a set with the fields set in `inject`."""
        return {self._BAGGAGE_HEADER_NAME}


def _split_baggage_entries(headers: Iterable[str]) -> Iterator[str]:
    """Yield the list-members of all baggage headers, combined as a single baggage string."""
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
    baggage_entries: Mapping[str, Any],
) -> Iterator[str]:
    """Yield 'key=value' pairs with percent-encoded values from baggage entries."""
    for key, value in baggage_entries.items():
        if not _is_valid_key(key):
            _logger.warning("Baggage key `%s` is not a valid token", key)
            continue
        yield str(key) + "=" + quote(str(value), safe="")
