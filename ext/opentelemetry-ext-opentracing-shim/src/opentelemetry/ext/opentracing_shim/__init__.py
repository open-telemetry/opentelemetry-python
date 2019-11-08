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

import logging

import opentracing
from deprecated import deprecated

import opentelemetry.trace as trace_api
from opentelemetry.ext.opentracing_shim import util

logger = logging.getLogger(__name__)


def create_tracer(otel_tracer):
    return TracerShim(otel_tracer)


class SpanContextShim(opentracing.SpanContext):
    def __init__(self, otel_context):
        self._otel_context = otel_context

    def unwrap(self):
        """Returns the wrapped OpenTelemetry `SpanContext` object."""

        return self._otel_context

    @property
    def baggage(self):
        logger.warning(
            "Using unimplemented property baggage on class %s.",
            self.__class__.__name__,
        )
        # TODO: Implement.


class SpanShim(opentracing.Span):
    def __init__(self, tracer, context, span):
        super().__init__(tracer, context)
        self._otel_span = span

    def unwrap(self):
        """Returns the wrapped OpenTelemetry `Span` object."""

        return self._otel_span

    def set_operation_name(self, operation_name):
        self._otel_span.update_name(operation_name)
        return self

    def finish(self, finish_time=None):
        end_time = finish_time
        if end_time is not None:
            end_time = util.time_seconds_to_ns(finish_time)
        self._otel_span.end(end_time=end_time)

    def set_tag(self, key, value):
        self._otel_span.set_attribute(key, value)
        return self

    def log_kv(self, key_values, timestamp=None):
        if timestamp is not None:
            event_timestamp = util.time_seconds_to_ns(timestamp)
        else:
            event_timestamp = None

        event_name = util.event_name_from_kv(key_values)
        self._otel_span.add_event(event_name, key_values, event_timestamp)
        return self

    @deprecated(reason="This method is deprecated in favor of log_kv")
    def log(self, **kwargs):
        super().log(**kwargs)

    @deprecated(reason="This method is deprecated in favor of log_kv")
    def log_event(self, event, payload=None):
        super().log_event(event, payload=payload)

    def set_baggage_item(self, key, value):
        logger.warning(
            "Calling unimplemented method set_baggage_item() on class %s",
            self.__class__.__name__,
        )
        # TODO: Implement.

    def get_baggage_item(self, key):
        logger.warning(
            "Calling unimplemented method get_baggage_item() on class %s",
            self.__class__.__name__,
        )
        # TODO: Implement.


class ScopeShim(opentracing.Scope):
    """A `ScopeShim` wraps the OpenTelemetry functionality related to span
    activation/deactivation while using OpenTracing `Scope` objects for
    presentation.

    There are two ways to construct a `ScopeShim` object: using the default
    initializer and using the `from_context_manager()` class method.

    It is necessary to have both ways for constructing `ScopeShim` objects
    because in some cases we need to create the object from a context manager,
    in which case our only way of retrieving a `Span` object is by calling the
    `__enter__()` method on the context manager, which makes the span active in
    the OpenTelemetry tracer; whereas in other cases we need to accept a
    `SpanShim` object and wrap it in a `ScopeShim`.
    """

    def __init__(self, manager, span, span_cm=None):
        super().__init__(manager, span)
        self._span_cm = span_cm

    # TODO: Change type of `manager` argument to `opentracing.ScopeManager`? We
    # need to get rid of `manager.tracer` for this.
    @classmethod
    def from_context_manager(cls, manager, span_cm):
        """Constructs a `ScopeShim` from an OpenTelemetry `Span` context
        manager (as returned by `Tracer.use_span()`).
        """

        otel_span = span_cm.__enter__()
        span_context = SpanContextShim(otel_span.get_context())
        span = SpanShim(manager.tracer, span_context, otel_span)
        return cls(manager, span, span_cm)

    def close(self):
        if self._span_cm is not None:
            # We don't have error information to pass to `__exit__()` so we
            # pass `None` in all arguments. If the OpenTelemetry tracer
            # implementation requires this information, the `__exit__()` method
            # on `opentracing.Scope` should be overridden and modified to pass
            # the relevant values to this `close()` method.
            self._span_cm.__exit__(None, None, None)
        else:
            self._span.unwrap().end()


class ScopeManagerShim(opentracing.ScopeManager):
    def __init__(self, tracer):
        # The only thing the `__init__()` method on the base class does is
        # initialize `self._noop_span` and `self._noop_scope` with no-op
        # objects. Therefore, it doesn't seem useful to call it.
        # pylint: disable=super-init-not-called
        self._tracer = tracer

    def activate(self, span, finish_on_close):
        span_cm = self._tracer.unwrap().use_span(
            span.unwrap(), end_on_exit=finish_on_close
        )
        return ScopeShim.from_context_manager(self, span_cm=span_cm)

    @property
    def active(self):
        span = self._tracer.unwrap().get_current_span()
        if span is None:
            return None

        span_context = SpanContextShim(span.get_context())
        wrapped_span = SpanShim(self._tracer, span_context, span)
        return ScopeShim(self, span=wrapped_span)
        # TODO: The returned `ScopeShim` instance here always ends the
        # corresponding span, regardless of the `finish_on_close` value used
        # when activating the span. This is because here we return a *new*
        # `ScopeShim` rather than returning a saved instance of `ScopeShim`.
        # https://github.com/open-telemetry/opentelemetry-python/pull/211/files#r335398792

    @property
    def tracer(self):
        return self._tracer


class TracerShim(opentracing.Tracer):
    def __init__(self, tracer):
        super().__init__(scope_manager=ScopeManagerShim(self))
        self._otel_tracer = tracer

    def unwrap(self):
        """Returns the wrapped OpenTelemetry `Tracer` object."""

        return self._otel_tracer

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
        return self._scope_manager.activate(span, finish_on_close)

    def start_span(
        self,
        operation_name=None,
        child_of=None,
        references=None,
        tags=None,
        start_time=None,
        ignore_active_span=False,
    ):
        # Use active span as parent when no explicit parent is specified.
        if not ignore_active_span and not child_of:
            child_of = self.active_span

        # Use the specified parent or the active span if possible. Otherwise,
        # use a `None` parent, which triggers the creation of a new trace.
        parent = child_of.unwrap() if child_of else None

        links = ()
        if references:
            links = []
            for ref in references:
                links.append(trace_api.Link(ref.referenced_context.unwrap()))

        span = self._otel_tracer.create_span(
            operation_name, parent, links=links
        )

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
        context = SpanContextShim(span.get_context())
        return SpanShim(self, context, span)

    def inject(self, span_context, format, carrier):
        # pylint: disable=redefined-builtin
        logger.warning(
            "Calling unimplemented method inject() on class %s",
            self.__class__.__name__,
        )
        # TODO: Implement.

    def extract(self, format, carrier):
        # pylint: disable=redefined-builtin
        logger.warning(
            "Calling unimplemented method extract() on class %s",
            self.__class__.__name__,
        )
        # TODO: Implement.
