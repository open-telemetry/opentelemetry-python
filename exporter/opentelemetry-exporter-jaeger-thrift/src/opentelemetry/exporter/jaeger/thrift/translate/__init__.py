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

from opentelemetry.exporter.jaeger.thrift.gen.jaeger import (
    Collector as TCollector,
)
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


def _append_dropped(tags, key, val):
    if val:
        tags.append(_get_long_tag(key, val))


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


def _get_string_tag(key, value: str) -> TCollector.Tag:
    """Returns jaeger string tag."""
    return TCollector.Tag(key=key, vStr=value, vType=TCollector.TagType.STRING)


def _get_bool_tag(key: str, value: bool) -> TCollector.Tag:
    """Returns jaeger boolean tag."""
    return TCollector.Tag(key=key, vBool=value, vType=TCollector.TagType.BOOL)


def _get_long_tag(key: str, value: int) -> TCollector.Tag:
    """Returns jaeger long tag."""
    return TCollector.Tag(key=key, vLong=value, vType=TCollector.TagType.LONG)


def _get_double_tag(key: str, value: float) -> TCollector.Tag:
    """Returns jaeger double tag."""
    return TCollector.Tag(
        key=key, vDouble=value, vType=TCollector.TagType.DOUBLE
    )


def _get_trace_id_low(trace_id):
    return _convert_int_to_i64(trace_id & 0xFFFFFFFFFFFFFFFF)


def _get_trace_id_high(trace_id):
    return _convert_int_to_i64((trace_id >> 64) & 0xFFFFFFFFFFFFFFFF)


def _translate_attribute(
    key: str, value: types.AttributeValue, max_length: Optional[int]
) -> Optional[TCollector.Tag]:
    """Convert the attributes to jaeger tags."""
    if isinstance(value, bool):
        return _get_bool_tag(key, value)
    if isinstance(value, str):
        if max_length is not None:
            value = value[:max_length]
        return _get_string_tag(key, value)
    if isinstance(value, int):
        return _get_long_tag(key, value)
    if isinstance(value, float):
        return _get_double_tag(key, value)
    if isinstance(value, tuple):
        value = str(value)
        if max_length is not None:
            value = value[:max_length]
        return _get_string_tag(key, value)
    return None


class ThriftTranslator(Translator):
    def _translate_span(self, span: ReadableSpan) -> TCollector.Span:
        ctx = span.get_span_context()
        trace_id = ctx.trace_id
        span_id = ctx.span_id

        start_time_us = _nsec_to_usec_round(span.start_time)
        duration_us = _nsec_to_usec_round(span.end_time - span.start_time)

        parent_id = span.parent.span_id if span.parent else 0

        tags = self._extract_tags(span)
        refs = self._extract_refs(span)
        logs = self._extract_logs(span)

        flags = int(ctx.trace_flags)

        jaeger_span = TCollector.Span(
            traceIdHigh=_get_trace_id_high(trace_id),
            traceIdLow=_get_trace_id_low(trace_id),
            spanId=_convert_int_to_i64(span_id),
            operationName=span.name,
            startTime=start_time_us,
            duration=duration_us,
            tags=tags,
            logs=logs,
            references=refs,
            flags=flags,
            parentSpanId=_convert_int_to_i64(parent_id),
        )
        return jaeger_span

    def _extract_tags(self, span: ReadableSpan) -> Sequence[TCollector.Tag]:
        # pylint: disable=too-many-branches
        translated = []
        if span.attributes:
            for key, value in span.attributes.items():
                tag = _translate_attribute(
                    key, value, self._max_tag_value_length
                )
                if tag:
                    translated.append(tag)
        if span.resource.attributes:
            for key, value in span.resource.attributes.items():
                tag = _translate_attribute(
                    key, value, self._max_tag_value_length
                )
                if tag:
                    translated.append(tag)

        status = span.status
        if status.status_code is not StatusCode.UNSET:
            translated.append(
                _get_string_tag("otel.status_code", status.status_code.name)
            )
            if status.description is not None:
                translated.append(
                    _get_string_tag(
                        "otel.status_description", status.description
                    )
                )

        translated.append(
            _get_string_tag("span.kind", OTLP_JAEGER_SPAN_KIND[span.kind])
        )

        # Instrumentation info tags
        if span.instrumentation_scope:
            name = _get_string_tag(NAME_KEY, span.instrumentation_scope.name)
            version = _get_string_tag(
                VERSION_KEY, span.instrumentation_scope.version
            )
            scope_name = _get_string_tag(
                _SCOPE_NAME_KEY, span.instrumentation_scope.name
            )
            scope_version = _get_string_tag(
                _SCOPE_VERSION_KEY, span.instrumentation_scope.version
            )

            translated.extend([name, version])
            translated.extend([scope_name, scope_version])

        # Make sure to add "error" tag if span status is not OK
        if not span.status.is_ok:
            translated.append(_get_bool_tag("error", True))

        _append_dropped(
            translated,
            "otel.dropped_attributes_count",
            span.dropped_attributes,
        )
        _append_dropped(
            translated, "otel.dropped_events_count", span.dropped_events
        )
        _append_dropped(
            translated, "otel.dropped_links_count", span.dropped_links
        )

        return translated

    def _extract_refs(
        self, span: ReadableSpan
    ) -> Optional[Sequence[TCollector.SpanRef]]:
        if not span.links:
            return None

        refs = []
        for link in span.links:
            trace_id = link.context.trace_id
            span_id = link.context.span_id
            refs.append(
                TCollector.SpanRef(
                    refType=TCollector.SpanRefType.FOLLOWS_FROM,
                    traceIdHigh=_get_trace_id_high(trace_id),
                    traceIdLow=_get_trace_id_low(trace_id),
                    spanId=_convert_int_to_i64(span_id),
                )
            )
        return refs

    def _extract_logs(
        self, span: ReadableSpan
    ) -> Optional[Sequence[TCollector.Log]]:
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
                tag = _translate_attribute(
                    key, value, self._max_tag_value_length
                )
                if tag:
                    fields.append(tag)

            _append_dropped(
                fields,
                "otel.dropped_attributes_count",
                event.attributes.dropped,
            )

            fields.append(
                TCollector.Tag(
                    key="message",
                    vType=TCollector.TagType.STRING,
                    vStr=event.name,
                )
            )

            event_timestamp_us = _nsec_to_usec_round(event.timestamp)
            logs.append(
                TCollector.Log(
                    timestamp=int(event_timestamp_us), fields=fields
                )
            )

        return logs
