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

from contextlib import contextmanager

import opentracing

from opentelemetry.trace import Event, Span, SpanContext, Tracer
from opentracingshim import util


def create_tracer(tracer: Tracer) -> opentracing.Tracer:
    return TracerWrapper(tracer)


class SpanContextWrapper(opentracing.SpanContext):
    def __init__(self, otel_context: SpanContext):
        self._otel_context = otel_context

    @property
    def otel_context(self):
        return self._otel_context

    @property
    def baggage(self):
        return {}
        # TODO: Implement.


class SpanWrapper(opentracing.Span):
    def __init__(self, tracer, context, span: Span):
        self._otel_span = span
        opentracing.Span.__init__(self, tracer, context)

    @property
    def otel_span(self):
        """Returns the OpenTelemetry span embedded in the SpanWrapper."""
        return self._otel_span

    @property
    def context(self):
        return self._context

    @property
    def tracer(self):
        return self._tracer

    def set_operation_name(self, operation_name):
        self._otel_span.update_name(operation_name)
        return self

    def finish(self, finish_time=None):
        self._otel_span.end()
        # TODO: Handle finish_time. The OpenTelemetry API doesn't currently
        # support setting end time on a span and we cannot assume that all
        # OpenTelemetry Tracer implementations have an `end_time` field.
        # https://github.com/open-telemetry/opentelemetry-python/issues/134

    def set_tag(self, key, value):
        self._otel_span.set_attribute(key, value)

    def log_kv(self, key_values, timestamp=None):
        if timestamp is None:
            timestamp = util.time_ns()

        event_name = util.event_name_from_kv(key_values)
        event = Event(event_name, timestamp, key_values)
        self._otel_span.add_lazy_event(event)

        # Return self for call chaining.
        return self

    def set_baggage_item(self, key, value):
        return self
        # TODO: Implement.

    def get_baggage_item(self, key):
        return None
        # TODO: Implement.

    # TODO: Verify calls to deprecated methods `log_event()` and `log()` on
    # base class work properly (it's probably fine because both methods call
    # `log_kv()`).


class ScopeWrapper(opentracing.Scope):
    def __init__(self, manager, span):
        # pylint: disable=super-init-not-called
        self._manager = manager
        self._span = span

    @property
    def span(self):
        return self._span

    @property
    def manager(self):
        return self._manager

    def close(self):
        self._span.finish()
        # TODO: Set active span on OpenTelemetry tracer.
        # https://github.com/open-telemetry/opentelemetry-python/issues/161#issuecomment-534136274


class ScopeManagerWrapper(opentracing.ScopeManager):
    def __init__(self, tracer: Tracer):
        # pylint: disable=super-init-not-called
        self._tracer = tracer

    @contextmanager
    def activate(self, span, finish_on_close):
        with self._tracer.use_span(
            span.otel_span, end_on_exit=finish_on_close
        ) as otel_span:
            wrapped_span = SpanWrapper(
                self._tracer, otel_span.get_context(), otel_span
            )
            yield ScopeWrapper(self, wrapped_span)

    @property
    def active(self):
        span = self._tracer.get_current_span()
        wrapped_span = SpanWrapper(self._tracer, span.get_context(), span)
        return ScopeWrapper(self, wrapped_span)


class TracerWrapper(opentracing.Tracer):
    def __init__(
        self, tracer: Tracer, scope_manager: ScopeManagerWrapper = None
    ):
        # pylint: disable=super-init-not-called
        self._otel_tracer = tracer
        if scope_manager is not None:
            self._scope_manager = scope_manager
        else:
            self._scope_manager = ScopeManagerWrapper(tracer)

    @property
    def scope_manager(self):
        return self._scope_manager

    @property
    def active_span(self):
        span = self._otel_tracer.get_current_span()
        if span is None:
            return None
        return SpanWrapper(self, span.get_context(), span)

    @contextmanager
    def start_active_span(
        self,
        operation_name,
        child_of=None,
        references=None,
        tags=None,
        start_time=None,
        ignore_active_span=False,
        finish_on_close=True,
    ) -> ScopeWrapper:
        span = self.start_span(
            operation_name=operation_name,
            child_of=child_of,
            references=references,
            tags=tags,
            start_time=start_time,
            ignore_active_span=ignore_active_span,
        )
        with self._scope_manager.activate(span, finish_on_close) as scope:
            yield scope

    def start_span(
        self,
        operation_name=None,
        child_of=None,
        references=None,
        tags=None,
        start_time=None,
        ignore_active_span=False,
    ) -> SpanWrapper:
        # TODO: Handle optional arguments.
        parent = child_of
        if parent is not None:
            if isinstance(parent, SpanWrapper):
                parent = child_of.otel_span
            elif isinstance(parent, SpanContextWrapper):
                parent = child_of.otel_context
            else:
                raise RuntimeError(
                    "Invalid parent type when calling start_span()."
                )

        span = self._otel_tracer.create_span(operation_name, parent)
        span.start()
        context = SpanContextWrapper(span.get_context())
        return SpanWrapper(self, context, span)

    def inject(self, span_context, format, carrier):
        # pylint: disable=redefined-builtin
        pass
        # TODO: Implement.

    def extract(self, format, carrier):
        # pylint: disable=redefined-builtin
        pass
        # TODO: Implement.
