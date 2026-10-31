# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Reading and writing the ``ot`` entry of the W3C trace state.

The entry value is a list of ``key:value`` members separated by ``;``. Two
keys are understood here: ``th`` holds the sampling threshold and ``rv`` holds
the 56-bit randomness value. Every other member is carried through untouched
so that a vendor sharing the entry does not lose its own data.

``th`` is hexadecimal, lowercase, at most 14 digits, with trailing zeros
removed, so ``th:8`` and ``th:80000000000000`` denote the same threshold of
one half. ``rv`` is hexadecimal and always exactly 14 digits.

Nothing in this module raises on malformed input. A member that cannot be read
leaves its field set to ``INVALID_THRESHOLD`` or ``INVALID_RANDOM_VALUE`` and
is then simply absent from anything written back out.

The encoding is defined by
https://opentelemetry.io/docs/specs/otel/trace/tracestate-probability-sampling/

Private to the ``_sampling_experimental`` subpackage, with no compatibility
guarantee.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from opentelemetry.trace import TraceState

from ._util import (
    INVALID_RANDOM_VALUE,
    INVALID_THRESHOLD,
    MAX_THRESHOLD,
    is_valid_random_value,
    is_valid_threshold,
)

OTEL_TRACE_STATE_KEY = "ot"

_TRACE_STATE_SIZE_LIMIT = 256
_MAX_VALUE_LENGTH = 14  # 56 bits, 4 bits per hex digit


@dataclass
class OtelTraceState:
    """Marshals OpenTelemetry tracestate for sampling parameters.

    https://opentelemetry.io/docs/specs/otel/trace/tracestate-probability-sampling/

    The dataclass is mutable on purpose: the composite sampler parses an
    incoming entry, overwrites ``threshold`` with the one it decided on, and
    serializes the same instance back out.

    Args:
        random_value: The 56-bit value read from the ``rv`` member, or
            ``INVALID_RANDOM_VALUE`` when the member was absent or unreadable.
        threshold: The threshold read from the ``th`` member with its trailing
            zeros restored, or ``INVALID_THRESHOLD`` when the member was
            absent or unreadable.
        rest: The members that were neither ``th`` nor ``rv``, in the order
            they appeared, each still in its original ``key:value`` form.
    """

    random_value: int
    threshold: int
    rest: Sequence[str]

    @staticmethod
    def invalid() -> OtelTraceState:
        """Build the state that carries no usable sampling information.

        Returns:
            An instance whose two fields hold their invalid sentinels and
            whose ``rest`` is empty, which ``serialize`` turns into the empty
            string.
        """
        return OtelTraceState(INVALID_RANDOM_VALUE, INVALID_THRESHOLD, ())

    @staticmethod
    def parse(trace_state: TraceState | None) -> OtelTraceState:
        """Read the ``ot`` entry out of a trace state.

        Members are split on ``;``. A duplicate ``th:`` or ``rv:`` member
        overwrites the earlier one, so the last occurrence wins, and a later
        unreadable duplicate discards a readable earlier value. A member whose
        value does not parse leaves its field at the invalid sentinel; no
        exception is raised and the remaining members are still read.

        The entry as a whole is rejected when it is empty or longer than 256
        characters, which takes its readable members down with it.

        Args:
            trace_state: The trace state inherited from the parent, or
                ``None``. ``None``, an empty trace state and a trace state
                with no ``ot`` entry are all treated the same way.

        Returns:
            The parsed state, or the result of ``invalid`` when there was
            nothing usable to read.
        """
        if not trace_state:
            return OtelTraceState.invalid()

        ot = trace_state.get(OTEL_TRACE_STATE_KEY, "")

        if not ot or len(ot) > _TRACE_STATE_SIZE_LIMIT:
            return OtelTraceState.invalid()

        threshold = INVALID_THRESHOLD
        random_value = INVALID_RANDOM_VALUE

        members = ot.split(";")
        rest: list[str] | None = None
        for member in members:
            if member.startswith("th:"):
                threshold = _parse_th(member[len("th:") :], INVALID_THRESHOLD)
                continue
            if member.startswith("rv:"):
                random_value = _parse_rv(member[len("rv:") :], INVALID_RANDOM_VALUE)
                continue
            if rest is None:
                rest = [member]
            else:
                rest.append(member)

        return OtelTraceState(random_value=random_value, threshold=threshold, rest=rest or ())

    def serialize(self) -> str:
        """Render the state back into an ``ot`` entry value.

        ``th`` is emitted only when the threshold is valid and is not
        ``MAX_THRESHOLD``, the threshold that samples nothing. ``th`` always
        comes first and ``rv`` second. ``rv`` is emitted whenever the
        randomness value is valid, so a value that arrived in the parent entry
        is passed on and one that was never there is not invented. The members
        in ``rest`` follow, in the order they were parsed.

        When the result exceeds 256 characters, trailing members are dropped
        one at a time until it fits. Once no ``;`` is left, the remaining
        single member is returned over the limit rather than dropped.

        Returns:
            The entry value, or the empty string when neither field is valid
            and ``rest`` is empty. The caller is expected to omit the ``ot``
            entry entirely in that case.
        """
        if not is_valid_threshold(self.threshold) and not is_valid_random_value(self.random_value) and not self.rest:
            return ""

        parts: list[str] = []
        if is_valid_threshold(self.threshold) and self.threshold != MAX_THRESHOLD:
            parts.append(f"th:{serialize_th(self.threshold)}")
        if is_valid_random_value(self.random_value):
            parts.append(f"rv:{_serialize_rv(self.random_value)}")
        if self.rest:
            parts.extend(self.rest)
        res = ";".join(parts)
        while len(res) > _TRACE_STATE_SIZE_LIMIT:
            delim_idx = res.rfind(";")
            if delim_idx == -1:
                break
            res = res[:delim_idx]
        return res


def _parse_th(value: str, default: int) -> int:
    """Decode the value of a ``th`` member into a threshold.

    The encoding drops trailing zeros, so the digits are left-aligned within
    14 hexadecimal digits and the missing ones are restored by shifting four
    bits per absent digit. Because 14 digits is 56 bits, the result satisfies
    ``is_valid_threshold`` for any text made of hexadecimal digits alone.
    ``int`` also accepts a leading sign and an underscore separator, and
    either of those can produce a value that is neither valid nor equal to
    the default, so test a parsed threshold with ``is_valid_threshold``
    rather than by comparing it against ``INVALID_THRESHOLD``.

    Args:
        value: The text after ``th:``, without the key or the colon.
        default: Returned when the text is empty, is longer than 14
            characters, or is not hexadecimal. Callers pass
            ``INVALID_THRESHOLD``.

    Returns:
        The decoded threshold, or ``default`` when the text is unusable.
    """
    if not value or len(value) > _MAX_VALUE_LENGTH:
        return default

    try:
        parsed = int(value, 16)
    except ValueError:
        return default

    # th value is compressed by removing all trailing zeros,
    # so we restore them to get the real value.
    trailing_zeros = _MAX_VALUE_LENGTH - len(value)
    return parsed << (trailing_zeros * 4)


def _parse_rv(value: str, default: int) -> int:
    """Decode the value of an ``rv`` member into a randomness value.

    Unlike ``th``, this encoding has no trailing-zero compression, so the
    length check is exact rather than an upper bound: 13 digits are rejected
    instead of being padded.

    Args:
        value: The text after ``rv:``, without the key or the colon.
        default: Returned when the text is not exactly 14 characters or is
            not hexadecimal. Callers pass ``INVALID_RANDOM_VALUE``.

    Returns:
        The decoded randomness value, or ``default`` when the text is
        unusable.
    """
    if not value or len(value) != _MAX_VALUE_LENGTH:
        return default

    try:
        return int(value, 16)
    except ValueError:
        return default


def serialize_th(threshold: int) -> str:
    """Encode a threshold as the value of a ``th`` member.

    The threshold is written as 14 lowercase hexadecimal digits and the
    trailing zeros are then stripped, which is the compression the ``ot``
    entry defines. ``MIN_THRESHOLD`` would strip to nothing, so it is special
    cased to ``"0"``.

    ``ComposableTraceIDRatioBased`` also calls this to build its description
    string, which is why the function is not underscore prefixed.

    Args:
        threshold: A threshold below ``MAX_THRESHOLD``. ``MAX_THRESHOLD``
            itself needs 15 digits and is never passed here, because neither
            caller emits a ``th`` for it.

    Returns:
        The compressed hexadecimal text, without the ``th:`` key.
    """
    if not threshold:
        return "0"
    return f"{threshold:014x}".rstrip("0")


def _serialize_rv(random_value: int) -> str:
    """Encode a randomness value as the value of an ``rv`` member.

    No compression applies, so the result is always 14 lowercase hexadecimal
    digits, zero padded on the left.

    Args:
        random_value: A value that ``is_valid_random_value`` accepts.

    Returns:
        The hexadecimal text, without the ``rv:`` key.
    """
    return f"{random_value:014x}"
