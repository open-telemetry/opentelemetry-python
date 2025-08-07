from dataclasses import dataclass
from typing import Optional, Sequence

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
    random_value: int
    threshold: int
    rest: Sequence[str]

    @staticmethod
    def invalid() -> "OtelTraceState":
        return OtelTraceState(INVALID_RANDOM_VALUE, INVALID_THRESHOLD, ())

    @staticmethod
    def parse(trace_state: Optional[TraceState]) -> "OtelTraceState":
        if not trace_state:
            return OtelTraceState.invalid()

        ot = trace_state.get(OTEL_TRACE_STATE_KEY, "")

        if not ot or len(ot) > _TRACE_STATE_SIZE_LIMIT:
            return OtelTraceState.invalid()

        threshold = INVALID_THRESHOLD
        random_value = INVALID_RANDOM_VALUE

        members = ot.split(";")
        rest: Optional[list[str]] = None
        for member in members:
            if member.startswith("th:"):
                threshold = _parse_th(member[len("th:") :], INVALID_THRESHOLD)
                continue
            if member.startswith("rv:"):
                random_value = _parse_rv(
                    member[len("rv:") :], INVALID_RANDOM_VALUE
                )
                continue
            if rest is None:
                rest = [member]
            else:
                rest.append(member)

        return OtelTraceState(
            random_value=random_value, threshold=threshold, rest=rest or ()
        )

    def serialize(self) -> str:
        if (
            not is_valid_threshold(self.threshold)
            and not is_valid_random_value(self.random_value)
            and not self.rest
        ):
            return ""

        parts: list[str] = []
        if (
            is_valid_threshold(self.threshold)
            and self.threshold != MAX_THRESHOLD
        ):
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
    if not value or len(value) > _MAX_VALUE_LENGTH:
        return default

    try:
        parsed = int(value, 16)
    except ValueError:
        return default

    trailing_zeros = _MAX_VALUE_LENGTH - len(value)
    return parsed << (trailing_zeros * 4)


def _parse_rv(value: str, default: int) -> int:
    if not value or len(value) != _MAX_VALUE_LENGTH:
        return default

    try:
        return int(value, 16)
    except ValueError:
        return default


def serialize_th(threshold: int) -> str:
    if not threshold:
        return "0"
    return f"{threshold:014x}".rstrip("0")


def _serialize_rv(random_value: int) -> str:
    return f"{random_value:014x}"
