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
from opencensus.trace.blank_span import BlankSpan
from opencensus.trace.tracers.base import Tracer as BaseTracer

from opentelemetry import context, trace
from opentelemetry.shim.opencensus._shim_span import ShimSpan

_logger = logging.getLogger(__name__)

_SHIM_SPAN_KEY = context.create_key("opencensus-shim-span-key")


def set_shim_span_in_context(
    span: ShimSpan, ctx: context.Context
) -> context.Context:
    return context.set_value(_SHIM_SPAN_KEY, span, ctx)


def get_shim_span_in_context() -> ShimSpan:
    return context.get_value(_SHIM_SPAN_KEY)


# pylint: disable=abstract-method
class ShimTracer(wrapt.ObjectProxy):
    def __init__(
        self, wrapped: BaseTracer, *, otel_tracer: trace.Tracer
    ) -> None:
        super().__init__(wrapped)
        self._self_otel_tracer = otel_tracer

    # For now, finish() is not implemented by the shim. It would require keeping a list of all
    # spans created so they can all be finished.
    # def finish(self):
    #    """End spans and send to reporter."""

    def span(self, name="span"):
        return self.start_span(name=name)

    def start_span(self, name="span"):
        span = self._self_otel_tracer.start_span(name)
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
        return shim_span

    def end_span(self):
        """Finishes the current span in the context and pops restores the context from before
        the span was started.
        """
        span = self.current_span()
        if not span:
            _logger.warning("No active span, cannot do end_span.")
            return

        span.finish()
        # pylint: disable=protected-access
        context.detach(span._self_token)

    # pylint: disable=no-self-use
    def current_span(self):
        return get_shim_span_in_context()

    def add_attribute_to_current_span(self, attribute_key, attribute_value):
        self.current_span().add_attribute(attribute_key, attribute_value)
