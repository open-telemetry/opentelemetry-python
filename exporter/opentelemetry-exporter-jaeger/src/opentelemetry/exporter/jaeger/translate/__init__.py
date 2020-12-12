from abc import ABC, abstractmethod
from typing import Any, Sequence, Union, Optional

from opentelemetry.exporter.jaeger.gen.jaeger import Collector as TCollector
from opentelemetry.sdk.trace import Span
from opentelemetry.trace import SpanKind
from opentelemetry.util import types

OTLP_JAEGER_SPAN_KIND = {
    SpanKind.CLIENT: "client",
    SpanKind.SERVER: "server",
    SpanKind.CONSUMER: "consumer",
    SpanKind.PRODUCER: "producer",
    SpanKind.INTERNAL: "internal",
}

NAME_KEY = "otel.instrumentation_library.name"
VERSION_KEY = "otel.instrumentation_library.version"


def _nsec_to_usec_round(nsec: int) -> int:
    """Round nanoseconds to microseconds"""
    return (nsec + 500) // 10 ** 3


def _nsec_to_sec_round(nsec: int) -> int:
    """Round nanoseconds to seconds"""
    return (nsec + 500) // 10 ** 9


def _nsec_to_nanos(nsec: int) -> int:
    return int(nsec - _nsec_to_sec_round(nsec) * 1e9)


def _convert_int_to_i64(val):
    """Convert integer to signed int64 (i64)"""
    if val > 0x7FFFFFFFFFFFFFFF:
        val -= 0x10000000000000000
    return val


def _int_to_bytes(val: int) -> bytes:
    return val.to_bytes((val.bit_length() + 7) // 8, "big")
