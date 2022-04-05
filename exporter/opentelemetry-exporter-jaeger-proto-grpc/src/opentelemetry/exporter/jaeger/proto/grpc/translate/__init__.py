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

import abc
from typing import Optional, Sequence

from google.protobuf.duration_pb2 import Duration
from google.protobuf.timestamp_pb2 import Timestamp

from opentelemetry.exporter.jaeger.proto.grpc.gen import model_pb2

from opentelemetry.sdk.trace import ReadableSpan, StatusCode
from opentelemetry.trace import SpanKind
from opentelemetry.util import types


OTLP_JAEGER_SPAN_KIND = {
    SpanKind.CLIENT: "client",
    SpanKind.SERVER: "server",
    SpanKind.CONSUMER: "consumer",
    SpanKind.PRODUCER: "producer",
    SpanKind.INTERNAL: "internal",
}

NAME_KEY = "otel.library.name"
VERSION_KEY = "otel.library.version"
_SCOPE_NAME_KEY = "otel.scope.name"
_SCOPE_VERSION_KEY = "otel.scope.version"


def _nsec_to_usec_round(nsec: int) -> int:
    """Round nanoseconds to microseconds"""
    return (nsec + 500) // 10**3


def _convert_int_to_i64(val):
    """Convert integer to signed int64 (i64)"""
    if val > 0x7FFFFFFFFFFFFFFF:
        val -= 0x10000000000000000
    return val


class Translator(abc.ABC):
    def __init__(self, max_tag_value_length: Optional[int] = None):
        self._max_tag_value_length = max_tag_value_length

    @abc.abstractmethod
    def _translate_span(self, span):
        """Translates span to jaeger format.

        Args:
            span: span to translate
        """

    @abc.abstractmethod
    def _extract_tags(self, span):
        """Extracts tags from span and returns list of jaeger Tags.

        Args:
            span: span to extract tags
        """

    @abc.abstractmethod
    def _extract_refs(self, span):
        """Extracts references from span and returns list of jaeger SpanRefs.

        Args:
            span: span to extract references
        """

    @abc.abstractmethod
    def _extract_logs(self, span):
        """Extracts logs from span and returns list of jaeger Logs.

        Args:
            span: span to extract logs
        """


class Translate:
    def __init__(self, spans):
        self.spans = spans

    def _translate(self, translator: Translator):
        translated_spans = []
        for span in self.spans:
            # pylint: disable=protected-access
            translated_span = translator._translate_span(span)
            translated_spans.append(translated_span)
        return translated_spans


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
    key: str, value: types.AttributeValue, max_length: Optional[int]
) -> Optional[model_pb2.KeyValue]:
    """Convert the attributes to jaeger keyvalues."""
    translated = None
    if isinstance(value, bool):
        translated = _get_bool_key_value(key, value)
    elif isinstance(value, str):
        if max_length is not None:
            value = value[:max_length]
        translated = _get_string_key_value(key, value)
    elif isinstance(value, int):
        translated = _get_long_key_value(key, value)
    elif isinstance(value, float):
        translated = _get_double_key_value(key, value)
    elif isinstance(value, tuple):
        value = str(value)
        if max_length is not None:
            value = value[:max_length]
        translated = _get_string_key_value(key, value)
    return translated


def _extract_resource_tags(
    span: ReadableSpan, max_tag_value_length: Optional[int]
) -> Sequence[model_pb2.KeyValue]:
    """Extracts resource attributes from span and returns
    list of jaeger keyvalues.

    Args:
        span: span to extract keyvalues
    """
    tags = []
    for key, value in span.resource.attributes.items():
        tag = _translate_attribute(key, value, max_tag_value_length)
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
        seconds=end.seconds - start.seconds,
        nanos=end.nanos - start.nanos,
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
    def __init__(
        self, svc_name: str, max_tag_value_length: Optional[int] = None
    ):
        super().__init__(max_tag_value_length)
        self.svc_name = svc_name

    def _translate_span(self, span: ReadableSpan) -> model_pb2.Span:

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
            service_name=self.svc_name,
            tags=_extract_resource_tags(span, self._max_tag_value_length),
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

    def _extract_tags(
        self, span: ReadableSpan
    ) -> Sequence[model_pb2.KeyValue]:
        translated = []
        if span.attributes:
            for key, value in span.attributes.items():
                key_value = _translate_attribute(
                    key, value, self._max_tag_value_length
                )
                if key_value is not None:
                    translated.append(key_value)
        if span.resource.attributes:
            for key, value in span.resource.attributes.items():
                key_value = _translate_attribute(
                    key, value, self._max_tag_value_length
                )
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

        # Instrumentation scope KeyValues
        if span.instrumentation_scope:
            name = _get_string_key_value(
                NAME_KEY, span.instrumentation_scope.name
            )
            version = _get_string_key_value(
                VERSION_KEY, span.instrumentation_scope.version
            )
            scope_name = _get_string_key_value(
                _SCOPE_NAME_KEY, span.instrumentation_scope.name
            )
            scope_version = _get_string_key_value(
                _SCOPE_VERSION_KEY, span.instrumentation_scope.version
            )
            translated.extend([name, version])
            translated.extend([scope_name, scope_version])

        # Make sure to add "error" tag if span status is not OK
        if not span.status.is_ok:
            translated.append(_get_bool_key_value("error", True))

        if span.dropped_attributes:
            translated.append(
                _get_long_key_value(
                    "otel.dropped_attributes_count", span.dropped_attributes
                )
            )
        if span.dropped_events:
            translated.append(
                _get_long_key_value(
                    "otel.dropped_events_count", span.dropped_events
                )
            )
        if span.dropped_links:
            translated.append(
                _get_long_key_value(
                    "otel.dropped_links_count", span.dropped_links
                )
            )
        return translated

    def _extract_refs(
        self, span: ReadableSpan
    ) -> Optional[Sequence[model_pb2.SpanRef]]:

        refs = []
        if span.parent:
            ctx = span.get_span_context()
            parent_id = span.parent.span_id
            parent_ref = model_pb2.SpanRef(
                ref_type=model_pb2.SpanRefType.CHILD_OF,
                trace_id=_trace_id_to_bytes(ctx.trace_id),
                span_id=_span_id_to_bytes(parent_id),
            )
            refs.append(parent_ref)

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

    def _extract_logs(
        self, span: ReadableSpan
    ) -> Optional[Sequence[model_pb2.Log]]:
        if not span.events:
            return None

        logs = []
        for event in span.events:
            fields = []
            for key, value in event.attributes.items():
                tag = _translate_attribute(
                    key, value, self._max_tag_value_length
                )
                if tag:
                    fields.append(tag)

            if event.attributes.dropped:
                fields.append(
                    _translate_attribute(
                        "otel.dropped_attributes_count",
                        event.attributes.dropped,
                        self._max_tag_value_length,
                    )
                )

            fields.append(
                _get_string_key_value(
                    key="message",
                    value=event.name,
                )
            )
            event_ts = _proto_timestamp_from_epoch_nanos(event.timestamp)
            logs.append(model_pb2.Log(timestamp=event_ts, fields=fields))

        return logs
