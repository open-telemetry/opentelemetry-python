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

from opentelemetry.trace import Event
from opentracingshim import util


def create_tracer(tracer):
    return TracerWrapper(tracer)


class SpanContextWrapper(opentracing.SpanContext):
    def __init__(self, otel_context):
        self._otel_context = otel_context

    def unwrap(self):
        """Returns the wrapped OpenTelemetry `SpanContext` object."""

        return self._otel_context

    @property
    def baggage(self):
        raise NotImplementedError
        # TODO: Implement.


class SpanWrapper(opentracing.Span):
    def __init__(self, tracer, context, span):
        self._otel_span = span
        opentracing.Span.__init__(self, tracer, context)

    def unwrap(self):
        """Returns the wrapped OpenTelemetry `Span` object."""

        return self._otel_span

    @property
    def context(self):
        return self._context

    @property
    def tracer(self):
        return self._tracer

    def set_operation_name(self, operation_name):
        self._otel_span.update_name(operation_name)

        # Return self for call chaining.
        return self

    def finish(self, finish_time=None):
        end_time = finish_time
        if end_time is not None:
            end_time = util.time_seconds_to_ns(finish_time)
        self._otel_span.end(end_time=end_time)

    def set_tag(self, key, value):
        self._otel_span.set_attribute(key, value)

        # Return self for call chaining.
        return self

    def log_kv(self, key_values, timestamp=None):
        if timestamp is None:
            timestamp = util.time_ns()

        event_name = util.event_name_from_kv(key_values)
        event = Event(event_name, timestamp, key_values)
        self._otel_span.add_lazy_event(event)

        # Return self for call chaining.
        return self

    def set_baggage_item(self, key, value):
        raise NotImplementedError
        # TODO: Implement.

    def get_baggage_item(self, key):
        raise NotImplementedError
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
    def __init__(self, tracer):
        # pylint: disable=super-init-not-called
        self._tracer = tracer

    @contextmanager
    def activate(self, span, finish_on_close):
        with self._tracer.unwrap().use_span(
            span.unwrap(), end_on_exit=finish_on_close
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
    def __init__(self, tracer, scope_manager=None):
        # pylint: disable=super-init-not-called
        self._otel_tracer = tracer
        if scope_manager is not None:
            self._scope_manager = scope_manager
        else:
            self._scope_manager = ScopeManagerWrapper(self)

    def unwrap(self):
        """Returns the wrapped OpenTelemetry `Tracer` object."""

        return self._otel_tracer

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
    ):
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
    ):
        parent = child_of
        if parent is not None:
            if isinstance(parent, SpanWrapper):
                parent = child_of.unwrap()
            elif isinstance(parent, SpanContextWrapper):
                parent = child_of.unwrap()
            else:
                raise RuntimeError(
                    "Invalid parent type when calling start_span()."
                )
            # TODO: Should we use the OpenTracing base classes for the type
            # check?

        # Use active span as parent when no explicit parent is specified.
        if (
            self.active_span is not None
            and not ignore_active_span
            and not parent
        ):
            parent = self.active_span.unwrap()

        span = self._otel_tracer.create_span(operation_name, parent)

        if references:
            if not isinstance(references, list):
                references = [references]
            for ref in references:
                span.add_link(ref.referenced_context.unwrap())

        if tags:
            for key, value in tags.items():
                span.set_attribute(key, value)

        # The OpenTracing API expects time values to be `float` values which
        # represent the number of seconds since the epoch. OpenTelemetry
        # represents time values as nanoseconds since the epoch.
        start_time_ns = start_time
        if start_time_ns is not None:
            start_time_ns = util.time_seconds_to_ns(start_time)

        span.start(start_time=start_time_ns)
        context = SpanContextWrapper(span.get_context())
        return SpanWrapper(self, context, span)

    def inject(self, span_context, format, carrier):
        # pylint: disable=redefined-builtin
        raise NotImplementedError
        # TODO: Implement.

    def extract(self, format, carrier):
        # pylint: disable=redefined-builtin
        raise NotImplementedError
        # TODO: Implement.
