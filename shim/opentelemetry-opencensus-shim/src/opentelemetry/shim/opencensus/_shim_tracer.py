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

import wrapt
from opencensus.trace import execution_context
from opencensus.trace.blank_span import BlankSpan
from opencensus.trace.span_context import SpanContext
from opencensus.trace.tracers.base import Tracer as BaseTracer
from opencensus.trace.tracestate import Tracestate

from opentelemetry import context, trace
from opentelemetry.shim.opencensus._shim_span import ShimSpan

_logger = logging.getLogger(__name__)

_SHIM_SPAN_KEY = context.create_key("opencensus-shim-span-key")
_SAMPLED = trace.TraceFlags(trace.TraceFlags.SAMPLED)


def set_shim_span_in_context(
    span: ShimSpan, ctx: context.Context
) -> context.Context:
    return context.set_value(_SHIM_SPAN_KEY, span, ctx)


def get_shim_span_in_context() -> ShimSpan:
    return context.get_value(_SHIM_SPAN_KEY)


def set_oc_span_in_context(
    oc_span_context: SpanContext, ctx: context.Context
) -> context.Context:
    """Returns a new OTel context based on ctx with oc_span_context set as the current span"""

    # If no SpanContext is passed to the opencensus.trace.tracer.Tracer, it creates a new one
    # with a random trace ID and a None span ID to be the parent:
    # https://github.com/census-instrumentation/opencensus-python/blob/2e08df591b507612b3968be8c2538dedbf8fab37/opencensus/trace/tracer.py#L47.
    #
    # OpenTelemetry considers this an invalid SpanContext and will ignore it, so we can just
    # return early
    if oc_span_context.span_id is None:
        return ctx

    trace_id = int(oc_span_context.trace_id, 16)
    span_id = int(oc_span_context.span_id, 16)
    is_remote = oc_span_context.from_header
    trace_flags = (
        _SAMPLED if oc_span_context.trace_options.get_enabled() else None
    )
    trace_state = (
        trace.TraceState(tuple(oc_span_context.tracestate.items()))
        # OC SpanContext does not validate this type
        if isinstance(oc_span_context.tracestate, Tracestate)
        else None
    )

    return trace.set_span_in_context(
        trace.NonRecordingSpan(
            trace.SpanContext(
                trace_id=trace_id,
                span_id=span_id,
                is_remote=is_remote,
                trace_flags=trace_flags,
                trace_state=trace_state,
            )
        )
    )


# pylint: disable=abstract-method
class ShimTracer(wrapt.ObjectProxy):
    def __init__(
        self,
        wrapped: BaseTracer,
        *,
        oc_span_context: SpanContext,
        otel_tracer: trace.Tracer
    ) -> None:
        super().__init__(wrapped)
        self._self_oc_span_context = oc_span_context
        self._self_otel_tracer = otel_tracer

    # For now, finish() is not implemented by the shim. It would require keeping a list of all
    # spans created so they can all be finished.
    # def finish(self):
    #    """End spans and send to reporter."""

    def span(self, name="span"):
        return self.start_span(name=name)

    def start_span(self, name="span"):
        parent_ctx = context.get_current()
        # If there is no current span in context, use the one provided to the OC Tracer at
        # creation time
        if trace.get_current_span(parent_ctx) is trace.INVALID_SPAN:
            parent_ctx = set_oc_span_in_context(
                self._self_oc_span_context, parent_ctx
            )

        span = self._self_otel_tracer.start_span(name, context=parent_ctx)
        shim_span = ShimSpan(
            BlankSpan(name=name, context_tracer=self),
            otel_span=span,
            shim_tracer=self,
        )

        ctx = trace.set_span_in_context(span)
        ctx = set_shim_span_in_context(shim_span, ctx)

        # OpenCensus's ContextTracer calls execution_context.set_current_span(span) which is
        # equivalent to the below. This can cause context to leak but is equivalent.
        # pylint: disable=protected-access
        shim_span._self_token = context.attach(ctx)
        # Also set it in OC's context, equivalent to
        # https://github.com/census-instrumentation/opencensus-python/blob/2e08df591b507612b3968be8c2538dedbf8fab37/opencensus/trace/tracers/context_tracer.py#L94
        execution_context.set_current_span(shim_span)
        return shim_span

    def end_span(self):
        """Finishes the current span in the context and restores the context from before the
        span was started.
        """
        span = self.current_span()
        if not span:
            _logger.warning("No active span, cannot do end_span.")
            return

        span.finish()

        # pylint: disable=protected-access
        context.detach(span._self_token)
        # Also reset the OC execution_context, equivalent to
        # https://github.com/census-instrumentation/opencensus-python/blob/2e08df591b507612b3968be8c2538dedbf8fab37/opencensus/trace/tracers/context_tracer.py#L114-L117
        execution_context.set_current_span(self.current_span())

    # pylint: disable=no-self-use
    def current_span(self):
        return get_shim_span_in_context()

    def add_attribute_to_current_span(self, attribute_key, attribute_value):
        self.current_span().add_attribute(attribute_key, attribute_value)
