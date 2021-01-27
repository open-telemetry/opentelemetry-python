# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Optional, Sequence

from google.protobuf.duration_pb2 import Duration
from google.protobuf.timestamp_pb2 import Timestamp

from opentelemetry.exporter.jaeger.gen import model_pb2
from opentelemetry.exporter.jaeger.translate import (
    NAME_KEY,
    OTLP_JAEGER_SPAN_KIND,
    VERSION_KEY,
    Translator,
)
from opentelemetry.sdk.trace import Span, StatusCode
from opentelemetry.util import types

# pylint: disable=no-member,too-many-locals,no-self-use


def _trace_id_to_bytes(trace_id: int) -> bytes:
    """Returns bytes representation of trace id."""
    return trace_id.to_bytes(16, "big")


def _span_id_to_bytes(span_id: int) -> bytes:
    """Returns bytes representation of span id"""
    return span_id.to_bytes(8, "big")


def _get_string_key_value(key, value: str) -> model_pb2.KeyValue:
    """Returns jaeger string KeyValue."""
    return model_pb2.KeyValue(
        key=key, v_str=value, v_type=model_pb2.ValueType.STRING
    )


def _get_bool_key_value(key: str, value: bool) -> model_pb2.KeyValue:
    """Returns jaeger boolean KeyValue."""
    return model_pb2.KeyValue(
        key=key, v_bool=value, v_type=model_pb2.ValueType.BOOL
    )


def _get_long_key_value(key: str, value: int) -> model_pb2.KeyValue:
    """Returns jaeger long KeyValue."""
    return model_pb2.KeyValue(
        key=key, v_int64=value, v_type=model_pb2.ValueType.INT64
    )


def _get_double_key_value(key: str, value: float) -> model_pb2.KeyValue:
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
    elif isinstance(value, tuple):
        translated = _get_string_key_value(key, str(value))
    return translated


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
    """Compute Duration from two Timestamps.

    See https://developers.google.com/protocol-buffers/docs/reference/google.protobuf#duration
    """
    duration = Duration(
        seconds=end.seconds - start.seconds, nanos=end.nanos - start.nanos,
    )
    # pylint: disable=chained-comparison
    if duration.seconds < 0 and duration.nanos > 0:
        duration.seconds += 1
        duration.nanos -= 1000000000
    elif duration.seconds > 0 and duration.nanos < 0:
        duration.seconds -= 1
        duration.nanos += 1000000000
    return duration


def _proto_timestamp_from_epoch_nanos(nsec: int) -> Timestamp:
    """Create a Timestamp from the number of nanoseconds elapsed from the epoch.

    See https://developers.google.com/protocol-buffers/docs/reference/google.protobuf#timestamp
    """
    nsec_time = nsec / 1e9
    seconds = int(nsec_time)
    nanos = int((nsec_time - seconds) * 1e9)
    return Timestamp(seconds=seconds, nanos=nanos)


class ProtobufTranslator(Translator):
    def __init__(self, svc_name):
        self.svc_name = svc_name

    def _translate_span(self, span: Span) -> model_pb2.Span:

        ctx = span.get_span_context()
        # pb2 span expects in byte format
        trace_id = _trace_id_to_bytes(ctx.trace_id)
        span_id = _span_id_to_bytes(ctx.span_id)

        start_time = _proto_timestamp_from_epoch_nanos(span.start_time)
        end_time = _proto_timestamp_from_epoch_nanos(span.end_time)
        duration = _duration_from_two_time_stamps(start_time, end_time)

        tags = self._extract_tags(span)
        refs = self._extract_refs(span)
        logs = self._extract_logs(span)

        flags = int(ctx.trace_flags)

        process = model_pb2.Process(
            service_name=self.svc_name, tags=_extract_resource_tags(span)
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
        return jaeger_span

    def _extract_tags(self, span: Span) -> Sequence[model_pb2.KeyValue]:
        translated = []
        if span.attributes:
            for key, value in span.attributes.items():
                key_value = _translate_attribute(key, value)
                if key_value is not None:
                    translated.append(key_value)
        if span.resource.attributes:
            for key, value in span.resource.attributes.items():
                key_value = _translate_attribute(key, value)
                if key_value:
                    translated.append(key_value)

        status = span.status
        if status.status_code is not StatusCode.UNSET:
            translated.append(
                _get_string_key_value(
                    "otel.status_code", status.status_code.name
                )
            )
            if status.description is not None:
                translated.append(
                    _get_string_key_value(
                        "otel.status_description", status.description
                    )
                )
        translated.append(
            _get_string_key_value(
                "span.kind", OTLP_JAEGER_SPAN_KIND[span.kind]
            )
        )

        # Instrumentation info KeyValues
        if span.instrumentation_info:
            name = _get_string_key_value(
                NAME_KEY, span.instrumentation_info.name
            )
            version = _get_string_key_value(
                VERSION_KEY, span.instrumentation_info.version
            )
            translated.extend([name, version])

        # Make sure to add "error" tag if span status is not OK
        if not span.status.is_ok:
            translated.append(_get_bool_key_value("error", True))

        return translated

    def _extract_refs(
        self, span: Span
    ) -> Optional[Sequence[model_pb2.SpanRef]]:
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

    def _extract_logs(self, span: Span) -> Optional[Sequence[model_pb2.Log]]:
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
                _get_string_key_value(key="message", value=event.name,)
            )
            event_ts = _proto_timestamp_from_epoch_nanos(event.timestamp)
            logs.append(model_pb2.Log(timestamp=event_ts, fields=fields))

        return logs
