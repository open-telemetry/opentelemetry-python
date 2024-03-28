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

import logging
from datetime import datetime
from typing import TYPE_CHECKING

import wrapt
from opencensus.trace import execution_context
from opencensus.trace.blank_span import BlankSpan
from opencensus.trace.span import SpanKind
from opencensus.trace.status import Status
from opencensus.trace.time_event import MessageEvent

from opentelemetry import context, trace

if TYPE_CHECKING:
    from opentelemetry.shim.opencensus._shim_tracer import ShimTracer

_logger = logging.getLogger(__name__)

# Copied from Java
# https://github.com/open-telemetry/opentelemetry-java/blob/0d3a04669e51b33ea47b29399a7af00012d25ccb/opencensus-shim/src/main/java/io/opentelemetry/opencensusshim/SpanConverter.java#L24-L27
_MESSAGE_EVENT_ATTRIBUTE_KEY_TYPE = "message.event.type"
_MESSAGE_EVENT_ATTRIBUTE_KEY_SIZE_UNCOMPRESSED = (
    "message.event.size.uncompressed"
)
_MESSAGE_EVENT_ATTRIBUTE_KEY_SIZE_COMPRESSED = "message.event.size.compressed"

_MESSAGE_EVENT_TYPE_STR_MAPPING = {
    0: "TYPE_UNSPECIFIED",
    1: "SENT",
    2: "RECEIVED",
}


def _opencensus_time_to_nanos(timestamp: str) -> int:
    """Converts an OpenCensus formatted time string (ISO 8601 with Z) to time.time_ns style
    unix timestamp
    """
    # format taken from
    # https://github.com/census-instrumentation/opencensus-python/blob/c38c71b9285e71de94d0185ff3c5bf65ee163345/opencensus/common/utils/__init__.py#L76
    #
    # datetime.fromisoformat() does not work with the added "Z" until python 3.11
    seconds_float = datetime.strptime(
        timestamp, "%Y-%m-%dT%H:%M:%S.%fZ"
    ).timestamp()
    return round(seconds_float * 1e9)


# pylint: disable=abstract-method
class ShimSpan(wrapt.ObjectProxy):
    def __init__(
        self,
        wrapped: BlankSpan,
        *,
        otel_span: trace.Span,
        shim_tracer: "ShimTracer",
    ) -> None:
        super().__init__(wrapped)
        self._self_otel_span = otel_span
        self._self_shim_tracer = shim_tracer
        self._self_token: object = None

        # Set a few values for BlankSpan members (they appear to be part of the "public" API
        # even though they are not documented in BaseSpan). Some instrumentations may use these
        # and not expect an AttributeError to be raised. Set values from OTel where possible
        # and let ObjectProxy defer to the wrapped BlankSpan otherwise.
        sc = self._self_otel_span.get_span_context()
        self.same_process_as_parent_span = not sc.is_remote
        self.span_id = sc.span_id

    def span(self, name="child_span"):
        return self._self_shim_tracer.start_span(name=name)

    def add_attribute(self, attribute_key, attribute_value):
        self._self_otel_span.set_attribute(attribute_key, attribute_value)

    def add_annotation(self, description, **attrs):
        self._self_otel_span.add_event(description, attrs)

    def add_message_event(self, message_event: MessageEvent):
        attrs = {
            _MESSAGE_EVENT_ATTRIBUTE_KEY_TYPE: _MESSAGE_EVENT_TYPE_STR_MAPPING[
                message_event.type
            ],
        }
        if message_event.uncompressed_size_bytes is not None:
            attrs[_MESSAGE_EVENT_ATTRIBUTE_KEY_SIZE_UNCOMPRESSED] = (
                message_event.uncompressed_size_bytes
            )
        if message_event.compressed_size_bytes is not None:
            attrs[_MESSAGE_EVENT_ATTRIBUTE_KEY_SIZE_COMPRESSED] = (
                message_event.compressed_size_bytes
            )

        timestamp = _opencensus_time_to_nanos(message_event.timestamp)
        self._self_otel_span.add_event(
            str(message_event.id),
            attrs,
            timestamp=timestamp,
        )

    # pylint: disable=no-self-use
    def add_link(self, link):
        """span links do not work with the shim because the OpenCensus Tracer does not accept
        links in start_span(). Same issue applies to SpanKind. Also see:
        https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/compatibility/opencensus.md#known-incompatibilities
        """
        _logger.warning(
            "OpenTelemetry does not support links added after a span is created."
        )

    @property
    def span_kind(self):
        """Setting span_kind does not work with the shim because the OpenCensus Tracer does not
        accept the param in start_span() and there's no way to set OTel span kind after
        start_span().
        """
        return SpanKind.UNSPECIFIED

    @span_kind.setter
    def span_kind(self, value):
        _logger.warning(
            "OpenTelemetry does not support setting span kind after a span is created."
        )

    def set_status(self, status: Status):
        self._self_otel_span.set_status(
            trace.StatusCode.OK if status.is_ok else trace.StatusCode.ERROR,
            status.description,
        )

    def finish(self):
        """Note this method does not pop the span from current context. Use Tracer.end_span()
        or a `with span: ...` statement (contextmanager) to do that.
        """
        self._self_otel_span.end()

    def __enter__(self):
        self._self_otel_span.__enter__()
        return self

    # pylint: disable=arguments-differ
    def __exit__(self, exception_type, exception_value, traceback):
        self._self_otel_span.__exit__(
            exception_type, exception_value, traceback
        )
        # OpenCensus Span.__exit__() calls Tracer.end_span()
        # https://github.com/census-instrumentation/opencensus-python/blob/2e08df591b507612b3968be8c2538dedbf8fab37/opencensus/trace/span.py#L390
        # but that would cause the OTel span to be ended twice. Instead, this code just copies
        # the context teardown from that method.
        context.detach(self._self_token)
        execution_context.set_current_span(
            self._self_shim_tracer.current_span()
        )
