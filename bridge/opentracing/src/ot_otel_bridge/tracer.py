# Copyright 2019, OpenTelemetry Authors
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


"""
OpenTracing bridge: an OpenTracing tracer implementation using the
OpenTelemetry API.
"""

import time

import opentracing
from basictracer import BasicTracer
from basictracer.context import SpanContext
from basictracer.text_propagator import TextPropagator
from basictracer.util import generate_id
from opentracing.propagation import Format

from .span import BridgeSpan


def tracer(**kwargs):  # pylint: disable=unused-argument
    return _BridgeTracer()


class _BridgeTracer(BasicTracer):
    def __init__(self):
        """Initialize the bridge Tracer."""
        super(_BridgeTracer, self).__init__(recorder=None, scope_manager=None)
        self.register_propagator(Format.TEXT_MAP, TextPropagator())
        self.register_propagator(Format.HTTP_HEADERS, TextPropagator())

    # code for start_active_span() and start_span() inspired from the base
    # class BasicTracer from basictracer-python (Apache 2.0) and adapted:
    # https://github.com/opentracing/basictracer-python/blob/96ebe40eabd83f9976e71b8e5c6f20ded2e57df3/basictracer/tracer.py#L51

    def start_active_span(
        self,
        operation_name,
        child_of=None,
        references=None,
        tags=None,
        start_time=None,
        ignore_active_span=False,
        finish_on_close=True,
    ):
        # Do not call super(): we want to call start_span() in this subclass.

        # create a new Span
        span = self.start_span(
            operation_name=operation_name,
            child_of=child_of,
            references=references,
            tags=tags,
            start_time=start_time,
            ignore_active_span=ignore_active_span,
        )

        return self.scope_manager.activate(span, finish_on_close)

    def start_span(
        self,
        operation_name=None,
        child_of=None,
        references=None,
        tags=None,
        start_time=None,
        ignore_active_span=False,
    ):
        # Do not call super(): create a BridgeSpan instead

        start_time = time.time() if start_time is None else start_time

        # pylint: disable=len-as-condition

        # See if we have a parent_ctx in `references`
        parent_ctx = None
        if child_of is not None:
            parent_ctx = (
                child_of
                if isinstance(child_of, opentracing.SpanContext)
                else child_of.context
            )
        elif references is not None and len(references) > 0:
            # TODO only the first reference is currently used
            parent_ctx = references[0].referenced_context

        # retrieve the active SpanContext
        if not ignore_active_span and parent_ctx is None:
            scope = self.scope_manager.active
            if scope is not None:
                parent_ctx = scope.span.context

        # Assemble the child ctx
        ctx = SpanContext(span_id=generate_id())
        if parent_ctx is not None:
            # pylint: disable=protected-access
            if parent_ctx._baggage is not None:
                ctx._baggage = parent_ctx._baggage.copy()
            ctx.trace_id = parent_ctx.trace_id
            ctx.sampled = parent_ctx.sampled
        else:
            ctx.trace_id = generate_id()
            ctx.sampled = self.sampler.sampled(ctx.trace_id)

        otel_parent = None
        if isinstance(child_of, opentracing.Span) and hasattr(
            child_of, "otel_span"
        ):
            otel_parent = child_of.otel_span

        # Tie it all together
        return BridgeSpan(
            self,
            operation_name=operation_name,
            context=ctx,
            parent_id=(None if parent_ctx is None else parent_ctx.span_id),
            tags=tags,
            start_time=start_time,
            otel_parent=otel_parent,
        )

    def __enter__(self):
        return self
