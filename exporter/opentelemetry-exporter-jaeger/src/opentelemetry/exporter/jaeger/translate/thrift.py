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
# pylint: disable=no-self-use
from typing import Optional, Sequence

from opentelemetry.exporter.jaeger.gen.jaeger import Collector as TCollector
from opentelemetry.exporter.jaeger.translate import (
    NAME_KEY,
    OTLP_JAEGER_SPAN_KIND,
    VERSION_KEY,
    Translator,
    _convert_int_to_i64,
    _nsec_to_usec_round,
)
from opentelemetry.sdk.trace import Span, StatusCode
from opentelemetry.util import types


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
    key: str, value: types.AttributeValue
) -> Optional[TCollector.Tag]:
    """Convert the attributes to jaeger tags."""
    if isinstance(value, bool):
        return _get_bool_tag(key, value)
    if isinstance(value, str):
        return _get_string_tag(key, value)
    if isinstance(value, int):
        return _get_long_tag(key, value)
    if isinstance(value, float):
        return _get_double_tag(key, value)
    if isinstance(value, tuple):
        return _get_string_tag(key, str(value))
    return None


class ThriftTranslator(Translator):
    def _translate_span(self, span: Span) -> TCollector.Span:
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

    def _extract_tags(self, span: Span) -> Sequence[TCollector.Tag]:

        translated = []
        if span.attributes:
            for key, value in span.attributes.items():
                tag = _translate_attribute(key, value)
                if tag:
                    translated.append(tag)
        if span.resource.attributes:
            for key, value in span.resource.attributes.items():
                tag = _translate_attribute(key, value)
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
        if span.instrumentation_info:
            name = _get_string_tag(NAME_KEY, span.instrumentation_info.name)
            version = _get_string_tag(
                VERSION_KEY, span.instrumentation_info.version
            )
            translated.extend([name, version])

        # Make sure to add "error" tag if span status is not OK
        if not span.status.is_ok:
            translated.append(_get_bool_tag("error", True))

        return translated

    def _extract_refs(
        self, span: Span
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

    def _extract_logs(self, span: Span) -> Optional[Sequence[TCollector.Log]]:
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
