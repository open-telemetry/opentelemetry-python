from typing import Optional, Sequence

from google.protobuf.duration_pb2 import Duration
from google.protobuf.timestamp_pb2 import Timestamp

import opentelemetry.exporter.jaeger.gen.model_pb2 as model_pb2
from opentelemetry.exporter.jaeger.translate import (
    NAME_KEY,
    OTLP_JAEGER_SPAN_KIND,
    VERSION_KEY,
)
from opentelemetry.sdk.trace import Span
from opentelemetry.util import types

# pylint: disable=no-member,too-many-locals


def _trace_id_to_bytes(trace_id: int) -> bytes:
    """Returns bytes representation of trace id."""
    return trace_id.to_bytes(16, "big")


def _span_id_to_bytes(span_id: int) -> bytes:
    """Returns bytes representation of span id"""
    return span_id.to_bytes(8, "big")


def _get_string_key_value(
    key, value: types.AttributeValue
) -> model_pb2.KeyValue:
    """Returns jaeger string KeyValue."""
    return model_pb2.KeyValue(
        key=key, v_str=value, v_type=model_pb2.ValueType.STRING
    )


def _get_bool_key_value(
    key: str, value: types.AttributeValue
) -> model_pb2.KeyValue:
    """Returns jaeger boolean KeyValue."""
    return model_pb2.KeyValue(
        key=key, v_bool=value, v_type=model_pb2.ValueType.BOOL
    )


def _get_long_key_value(
    key: str, value: types.AttributeValue
) -> model_pb2.KeyValue:
    """Returns jaeger long KeyValue."""
    return model_pb2.KeyValue(
        key=key, v_int64=value, v_type=model_pb2.ValueType.INT64
    )


def _get_double_key_value(
    key: str, value: types.AttributeValue
) -> model_pb2.KeyValue:
    """Returns jaeger double KeyValue."""
    return model_pb2.KeyValue(
        key=key, v_float64=value, v_type=model_pb2.ValueType.FLOAT64
    )


def _get_binary_key_value(key: str, value: bytes) -> model_pb2.KeyValue:
    """Returns jaeger double KeyValue."""
    return model_pb2.KeyValue(
        key=key, v_binary=value, v_type=model_pb2.ValueType.BINARY
    )


def _translate_attribute(
    key: str, value: types.AttributeValue
) -> Optional[model_pb2.KeyValue]:
    """Convert the attributes to jaeger keyvalues."""
    translated = None
    if isinstance(value, bool):
        translated = _get_bool_key_value(key, value)
    elif isinstance(value, str):
        translated = _get_string_key_value(key, value)
    elif isinstance(value, int):
        translated = _get_long_key_value(key, value)
    elif isinstance(value, float):
        translated = _get_double_key_value(key, value)
    elif isinstance(value, bytes):
        translated = _get_binary_key_value(key, value)
    elif isinstance(value, tuple):
        translated = _get_string_key_value(key, str(value))
    return translated


def _extract_key_values(span: Span) -> Sequence[model_pb2.KeyValue]:
    """Extracts attributes from span and returns list of jaeger keyvalues.

    Args:
        span: span to extract keyvalues
    """
    translated = []
    if span.attributes:
        for key, value in span.attributes.items():
            key_value = _translate_attribute(key, value)
            if key_value:
                translated.append(key_value)
    if span.resource.attributes:
        for key, value in span.resource.attributes.items():
            key_value = _translate_attribute(key, value)
            if key_value:
                translated.append(key_value)

    code = _get_long_key_value("status.code", span.status.status_code.value)
    message = _get_string_key_value("status.message", span.status.description)
    kind = _get_string_key_value("span.kind", OTLP_JAEGER_SPAN_KIND[span.kind])
    translated.extend([code, message, kind])

    # Instrumentation info KeyValues
    if span.instrumentation_info:
        name = _get_string_key_value(NAME_KEY, span.instrumentation_info.name)
        version = _get_string_key_value(
            VERSION_KEY, span.instrumentation_info.version
        )
        translated.extend([name, version])

    # Make sure to add "error" tag if span status is not OK
    if not span.status.is_ok:
        translated.append(_get_bool_key_value("error", True))

    return translated


def _extract_refs(span: Span) -> Optional[Sequence[model_pb2.SpanRef]]:
    """Returns jaeger span references if links exists, otherwise None.

    Args:
        span: span to extract refs
    """
    if not span.links:
        return None

    refs = []
    for link in span.links:
        trace_id = link.context.trace_id
        span_id = link.context.span_id
        refs.append(
            model_pb2.SpanRef(
                ref_type=model_pb2.SpanRefType.FOLLOWS_FROM,
                trace_id=_trace_id_to_bytes(trace_id),
                span_id=_span_id_to_bytes(span_id),
            )
        )
    return refs


def _extract_logs(span: Span) -> Optional[Sequence[model_pb2.Log]]:
    """Returns jaeger logs if events exists, otherwise None.

    Args:
        span: span to extract logs
    """
    if not span.events:
        return None

    logs = []
    for event in span.events:
        fields = []
        for key, value in event.attributes.items():
            tag = _translate_attribute(key, value)
            if tag:
                fields.append(tag)

        fields.append(
            model_pb2.KeyValue(
                key="message",
                v_type=model_pb2.ValueType.STRING,
                v_str=event.name,
            )
        )
        event_ts = _proto_timestamp_from_epoch_nanos(event.timestamp)
        logs.append(model_pb2.Log(timestamp=event_ts, fields=fields))

    return logs


def _extract_resource_tags(span: Span) -> Sequence[model_pb2.KeyValue]:
    """Extracts resource attributes from span and returns
    list of jaeger keyvalues.

    Args:
        span: span to extract keyvalues
    """
    tags = []
    for key, value in span.resource.attributes.items():
        tag = _translate_attribute(key, value)
        if tag:
            tags.append(tag)
    return tags


def _duration_from_two_time_stamps(
    start: Timestamp, end: Timestamp
) -> Duration:
    """Compute Duration from two Timestamps."""
    duration = Duration(
        seconds=end.seconds - start.seconds, nanos=end.nanos - start.nanos,
    )
    if duration.seconds < 0 and duration.nanos > 0:
        duration.seconds += 1
        duration.nanos -= 1000000000
    elif duration.seconds > 0 and duration.nanos < 0:
        duration.seconds -= 1
        duration.nanos += 1000000000
    return duration


def _proto_timestamp_from_epoch_nanos(nsec: int) -> Timestamp:
    """Create a Timestamp from the number of nanoseconds
    elapsed from the epoch.
    """
    nsec_time = nsec / 1e9
    seconds = int(nsec_time)
    nanos = int((nsec_time - seconds) * 1e9)
    return Timestamp(seconds=seconds, nanos=nanos)


def _to_jaeger(
    spans: Sequence[Span], svc_name: str
) -> Sequence[model_pb2.Span]:
    """Translate the spans to Jaeger format.

    Args:
        spans: Tuple of spans to convert
    """
    jaeger_spans = []

    for span in spans:
        ctx = span.get_span_context()
        # pb2 span expects in byte format
        trace_id = _trace_id_to_bytes(ctx.trace_id)
        span_id = _span_id_to_bytes(ctx.span_id)

        start_time = _proto_timestamp_from_epoch_nanos(span.start_time)
        end_time = _proto_timestamp_from_epoch_nanos(span.end_time)
        duration = _duration_from_two_time_stamps(start_time, end_time)

        tags = _extract_key_values(span)
        refs = _extract_refs(span)
        logs = _extract_logs(span)

        flags = int(ctx.trace_flags)

        process = model_pb2.Process(
            service_name=svc_name, tags=_extract_resource_tags(span)
        )
        jaeger_span = model_pb2.Span(
            trace_id=trace_id,
            span_id=span_id,
            operation_name=span.name,
            references=refs,
            flags=flags,
            start_time=start_time,
            duration=duration,
            tags=tags,
            logs=logs,
            process=process,
        )
        jaeger_spans.append(jaeger_span)

    return jaeger_spans
