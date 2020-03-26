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

"""
The OpenTelemetry OpenTracing shim is a library which allows an easy migration
from OpenTracing to OpenTelemetry.

The shim consists of a set of classes which implement the OpenTracing Python
API while using OpenTelemetry constructs behind the scenes. Its purpose is to
allow applications which are already instrumented using OpenTracing to start
using OpenTelemetry with a minimal effort, without having to rewrite large
portions of the codebase.

To use the shim, a :class:`TracerShim` instance is created and then used as if
it were an "ordinary" OpenTracing :class:`opentracing.Tracer`, as in the
following example::

    import time

    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.ext.opentracing_shim import create_tracer

    # Tell OpenTelemetry which Tracer implementation to use.
    trace.set_tracer_provider(TracerProvider())

    # Create an OpenTelemetry Tracer.
    otel_tracer = trace.get_tracer(__name__)

    # Create an OpenTracing shim.
    shim = create_tracer(otel_tracer)

    with shim.start_active_span("ProcessHTTPRequest"):
        print("Processing HTTP request")
        # Sleeping to mock real work.
        time.sleep(0.1)
        with shim.start_active_span("GetDataFromDB"):
            print("Getting data from DB")
            # Sleeping to mock real work.
            time.sleep(0.2)

Note:
    While the OpenTracing Python API represents time values as the number of
    **seconds** since the epoch expressed as :obj:`float` values, the
    OpenTelemetry Python API represents time values as the number of
    **nanoseconds** since the epoch expressed as :obj:`int` values. This fact
    requires the OpenTracing shim to convert time values back and forth between
    the two representations, which involves floating point arithmetic.

    Due to the way computers represent floating point values in hardware,
    representation of decimal floating point values in binary-based hardware is
    imprecise by definition.

    The above results in **slight imprecisions** in time values passed to the
    shim via the OpenTracing API when comparing the value passed to the shim
    and the value stored in the OpenTelemetry :class:`opentelemetry.trace.Span`
    object behind the scenes. **This is not a bug in this library or in
    Python**. Rather, this is a generic problem which stems from the fact that
    not every decimal floating point number can be correctly represented in
    binary, and therefore affects other libraries and programming languages as
    well. More information about this problem can be found in the
    `Floating Point Arithmetic\\: Issues and Limitations`_ section of the
    Python documentation.

    While testing this library, the aforementioned imprecisions were observed
    to be of *less than a microsecond*.

.. _Floating Point Arithmetic\\: Issues and Limitations:
    https://docs.python.org/3/tutorial/floatingpoint.html
"""

# TODO: make pylint use 3p opentracing module for type inference
# pylint:disable=no-member

import logging

import opentracing
from deprecated import deprecated

import opentelemetry.trace as trace_api
from opentelemetry import propagators
from opentelemetry.ext.opentracing_shim import util
from opentelemetry.ext.opentracing_shim.version import __version__
from opentelemetry.trace import DefaultSpan
from opentelemetry.trace.propagation import (
    get_span_from_context,
    set_span_in_context,
)

logger = logging.getLogger(__name__)


def create_tracer(otel_tracer_provider):
    """Creates a :class:`TracerShim` object from the provided OpenTelemetry
    :class:`opentelemetry.trace.TracerProvider`.

    The returned :class:`TracerShim` is an implementation of
    :class:`opentracing.Tracer` using OpenTelemetry under the hood.

    Args:
        otel_tracer_provider: A :class:`opentelemetry.trace.TracerProvider` to be
            used for constructing the :class:`TracerShim`. A tracer from this
            source will be used to perform the actual tracing when user code is
            instrumented using the OpenTracing API.

    Returns:
        The created :class:`TracerShim`.
    """

    return TracerShim(otel_tracer_provider.get_tracer(__name__, __version__))


class SpanContextShim(opentracing.SpanContext):
    """Implements :class:`opentracing.SpanContext` by wrapping a
    :class:`opentelemetry.trace.SpanContext` object.

    Args:
        otel_context: A :class:`opentelemetry.trace.SpanContext` to be used for
            constructing the :class:`SpanContextShim`.
    """

    def __init__(self, otel_context):
        self._otel_context = otel_context

    def unwrap(self):
        """Returns the wrapped :class:`opentelemetry.trace.SpanContext`
        object.

        Returns:
            The :class:`opentelemetry.trace.SpanContext` object wrapped by this
            :class:`SpanContextShim`.
        """

        return self._otel_context

    @property
    def baggage(self):
        """Implements the ``baggage`` property from the base class.

        Warning:
            Not implemented yet.
        """

        logger.warning(
            "Using unimplemented property baggage on class %s.",
            self.__class__.__name__,
        )
        # TODO: Implement.


class SpanShim(opentracing.Span):
    """Implements :class:`opentracing.Span` by wrapping a
    :class:`opentelemetry.trace.Span` object.

    Args:
        tracer: The :class:`opentracing.Tracer` that created this `SpanShim`.
        context: A :class:`SpanContextShim` which contains the context for this
            :class:`SpanShim`.
        span: A :class:`opentelemetry.trace.Span` to wrap.
    """

    def __init__(self, tracer, context, span):
        super().__init__(tracer, context)
        self._otel_span = span

    def unwrap(self):
        """Returns the wrapped :class:`opentelemetry.trace.Span` object.

        Returns:
            The :class:`opentelemetry.trace.Span` object wrapped by this
            :class:`SpanShim`.
        """

        return self._otel_span

    def set_operation_name(self, operation_name):
        """Implements the ``set_operation_name()`` method from the base class.

        Updates the name of the wrapped OpenTelemetry span.

        Returns:
            Returns this :class:`SpanShim` instance to allow call chaining.
        """

        self._otel_span.update_name(operation_name)
        return self

    def finish(self, finish_time=None):
        """Implements the ``finish()`` method from the base class.

        Ends the OpenTelemetry span wrapped by this :class:`SpanShim`.

        If *finish_time* is provided, the time value is converted to the
        OpenTelemetry time format (number of nanoseconds since the epoch,
        expressed as an integer) and passed on to the OpenTelemetry tracer when
        ending the OpenTelemetry span. If *finish_time* isn't provided, it is
        up to the OpenTelemetry tracer implementation to generate a timestamp
        when ending the span.

        Args:
            finish_time(:obj:`float`, optional): An explicit finish time
                expressed as the number of seconds since the epoch as returned
                by :func:`time.time()`. Defaults to `None`.
        """

        end_time = finish_time
        if end_time is not None:
            end_time = util.time_seconds_to_ns(finish_time)
        self._otel_span.end(end_time=end_time)

    def set_tag(self, key, value):
        """Implements the ``set_tag()`` method from the base class.

        Sets an OpenTelemetry attribute on the wrapped OpenTelemetry span.

        Args:
            key(:obj:`str`): A tag key.
            value: A tag value. Can be one of :obj:`str`, :obj:`bool`,
                :obj:`int`, :obj:`float`

        Returns:
            Returns this :class:`SpanShim` instance to allow call chaining.
        """

        self._otel_span.set_attribute(key, value)
        return self

    def log_kv(self, key_values, timestamp=None):
        """Implements the ``log_kv()`` method from the base class.

        Logs an :class:`opentelemetry.trace.Event` for the wrapped
        OpenTelemetry span.

        Note:
            The OpenTracing API defines the values of *key_values* to be of any
            type. However, the OpenTelemetry API requires that the values be
            one of :obj:`str`, :obj:`bool`, :obj:`float`. Therefore, only these
            types are supported as values.

        Args:
            key_values(:obj:`dict`): A dict with :obj:`str` keys and values of
                type :obj:`str`, :obj:`bool` or :obj:`float`.

        Returns:
            Returns this :class:`SpanShim` instance to allow call chaining.
        """

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

    def set_baggage_item(self, key, value):  # pylint:disable=unused-argument
        """Implements the ``set_baggage_item()`` method from the base class.

        Warning:
            Not implemented yet.
        """

        logger.warning(
            "Calling unimplemented method set_baggage_item() on class %s",
            self.__class__.__name__,
        )
        # TODO: Implement.

    def get_baggage_item(self, key):  # pylint:disable=unused-argument
        """Implements the ``get_baggage_item()`` method from the base class.

        Warning:
            Not implemented yet.
        """

        logger.warning(
            "Calling unimplemented method get_baggage_item() on class %s",
            self.__class__.__name__,
        )
        # TODO: Implement.


class ScopeShim(opentracing.Scope):
    """A `ScopeShim` wraps the OpenTelemetry functionality related to span
    activation/deactivation while using OpenTracing :class:`opentracing.Scope`
    objects for presentation.

    Unlike other classes in this package, the `ScopeShim` class doesn't wrap an
    OpenTelemetry class because OpenTelemetry doesn't have the notion of
    "scope" (though it *does* have similar functionality).

    There are two ways to construct a `ScopeShim` object: using the default
    initializer and using the :meth:`from_context_manager()` class method.

    It is necessary to have both ways for constructing `ScopeShim` objects
    because in some cases we need to create the object from an OpenTelemetry
    `opentelemetry.trace.Span` context manager (as returned by
    :meth:`opentelemetry.trace.Tracer.use_span`), in which case our only way of
    retrieving a `opentelemetry.trace.Span` object is by calling the
    ``__enter__()`` method on the context manager, which makes the span active
    in the OpenTelemetry tracer; whereas in other cases we need to accept a
    `SpanShim` object and wrap it in a `ScopeShim`. The former is used mainly
    when the instrumentation code retrieves the currently-active span using
    `ScopeManagerShim.active`. The latter is mainly used when the
    instrumentation code activates a span using
    :meth:`ScopeManagerShim.activate`.

    Args:
        manager: The :class:`ScopeManagerShim` that created this
            :class:`ScopeShim`.
        span: The :class:`SpanShim` this :class:`ScopeShim` controls.
        span_cm(:class:`contextlib.AbstractContextManager`, optional): A
            Python context manager which yields an OpenTelemetry
            `opentelemetry.trace.Span` from its ``__enter__()`` method. Used
            by :meth:`from_context_manager` to store the context manager as
            an attribute so that it can later be closed by calling its
            ``__exit__()`` method. Defaults to `None`.

    TODO: Is :class:`contextlib.AbstractContextManager` the correct
          type for *span_cm*?
    """

    def __init__(self, manager, span, span_cm=None):
        super().__init__(manager, span)
        self._span_cm = span_cm

    # TODO: Change type of `manager` argument to `opentracing.ScopeManager`? We
    # need to get rid of `manager.tracer` for this.
    @classmethod
    def from_context_manager(cls, manager, span_cm):
        """Constructs a :class:`ScopeShim` from an OpenTelemetry
        `opentelemetry.trace.Span` context
        manager.

        The method extracts a `opentelemetry.trace.Span` object from the
        context manager by calling the context manager's ``__enter__()``
        method. This causes the span to start in the OpenTelemetry tracer.

        Example usage::

            span = otel_tracer.start_span("TestSpan")
            span_cm = otel_tracer.use_span(span)
            scope_shim = ScopeShim.from_context_manager(
                scope_manager_shim,
                span_cm=span_cm,
            )

        Args:
            manager: The :class:`ScopeManagerShim` that created this
                :class:`ScopeShim`.
            span_cm: A context manager as returned by
                :meth:`opentelemetry.trace.Tracer.use_span`.
        """

        otel_span = span_cm.__enter__()
        span_context = SpanContextShim(otel_span.get_context())
        span = SpanShim(manager.tracer, span_context, otel_span)
        return cls(manager, span, span_cm)

    def close(self):
        """Implements the `close()` method from :class:`opentracing.Scope`.

        Closes the `ScopeShim`. If the `ScopeShim` was created from a context
        manager, calling this method sets the active span in the
        OpenTelemetry tracer back to the span which was active before this
        `ScopeShim` was created. In addition, if the span represented by this
        `ScopeShim` was activated with the *finish_on_close* argument set to
        `True`, calling this method will end the span.

        Warning:
            In the current state of the implementation it is possible to create
            a `ScopeShim` directly from a `SpanShim`, that is - without using
            :meth:`from_context_manager()`. For that reason we need to be able
            to end the span represented by the `ScopeShim` in this case, too.
            Please note that closing a `ScopeShim` created this way (for
            example as returned by :meth:`ScopeManagerShim.active`) **always
            ends the associated span**, regardless of the value passed in
            *finish_on_close* when activating the span.
        """

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
    """Implements :class:`opentracing.ScopeManager` by setting and getting the
    active `opentelemetry.trace.Span` in the OpenTelemetry tracer.

    This class keeps a reference to a :class:`TracerShim` as an attribute. This
    reference is used to communicate with the OpenTelemetry tracer. It is
    necessary to have a reference to the :class:`TracerShim` rather than the
    :class:`opentelemetry.trace.Tracer` wrapped by it because when constructing
    a :class:`SpanShim` we need to pass a reference to a
    :class:`opentracing.Tracer`.

    Args:
        tracer: A :class:`TracerShim` to use for setting and getting active
            span state.
    """

    def __init__(self, tracer):
        # The only thing the ``__init__()``` method on the base class does is
        # initialize `self._noop_span` and `self._noop_scope` with no-op
        # objects. Therefore, it doesn't seem useful to call it.
        # pylint: disable=super-init-not-called
        self._tracer = tracer

    def activate(self, span, finish_on_close):
        """Implements the ``activate()`` method from the base class.

        Activates a :class:`SpanShim` and returns a :class:`ScopeShim` which
        represents the active span.

        Args:
            span: A :class:`SpanShim` to be activated.
            finish_on_close(:obj:`bool`): Determines whether the OpenTelemetry
                span should be ended when the returned :class:`ScopeShim` is
                closed.

        Returns:
            A :class:`ScopeShim` representing the activated span.
        """

        span_cm = self._tracer.unwrap().use_span(
            span.unwrap(), end_on_exit=finish_on_close
        )
        return ScopeShim.from_context_manager(self, span_cm=span_cm)

    @property
    def active(self):
        """Implements the ``active`` property from the base class.

        Returns a :class:`ScopeShim` object representing the currently-active
        span in the OpenTelemetry tracer.

        Returns:
            A :class:`ScopeShim` representing the active span in the
            OpenTelemetry tracer, or `None` if no span is currently active.

        Warning:
            Calling :meth:`ScopeShim.close` on the :class:`ScopeShim` returned
            by this property **always ends the corresponding span**, regardless
            of the *finish_on_close* value used when activating the span. This
            is a limitation of the current implementation of the OpenTracing
            shim and is likely to be handled in future versions.
        """

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
        """Returns the :class:`TracerShim` reference used by this
        :class:`ScopeManagerShim` for setting and getting the active span from
        the OpenTelemetry tracer.

        Returns:
            The :class:`TracerShim` used for setting and getting the active
            span.

        Warning:
            This property is *not* a part of the OpenTracing API. It used
            internally by the current implementation of the OpenTracing shim
            and will likely be removed in future versions.
        """

        return self._tracer


class TracerShim(opentracing.Tracer):
    """Implements :class:`opentracing.Tracer` by wrapping a
    :class:`opentelemetry.trace.Tracer` object.

    This wrapper class allows using an OpenTelemetry tracer as if it were an
    OpenTracing tracer. It exposes the same methods as an "ordinary"
    OpenTracing tracer, and uses OpenTelemetry transparently for performing the
    actual tracing.

    This class depends on the *OpenTelemetry API*. Therefore, any
    implementation of a :class:`opentelemetry.trace.Tracer` should work with
    this class.

    Args:
        tracer: A :class:`opentelemetry.trace.Tracer` to use for tracing. This
            tracer will be invoked by the shim to create actual spans.
    """

    def __init__(self, tracer):
        super().__init__(scope_manager=ScopeManagerShim(self))
        self._otel_tracer = tracer
        self._supported_formats = (
            opentracing.Format.TEXT_MAP,
            opentracing.Format.HTTP_HEADERS,
        )

    def unwrap(self):
        """Returns the :class:`opentelemetry.trace.Tracer` object that is
        wrapped by this :class:`TracerShim` and used for actual tracing.

        Returns:
            The :class:`opentelemetry.trace.Tracer` used for actual tracing.
        """

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
        """Implements the ``start_active_span()`` method from the base class.

        Starts and activates a span. In terms of functionality, this method
        behaves exactly like the same method on a "regular" OpenTracing tracer.
        See :meth:`opentracing.Tracer.start_active_span` for more details.

        Args:
            operation_name(:obj:`str`): Name of the operation represented by
                the new span from the perspective of the current service.
            child_of(:class:`SpanShim` or :class:`SpanContextShim`, optional):
                A :class:`SpanShim` or :class:`SpanContextShim` representing
                the parent in a "child of" reference. If specified, the
                *references* parameter must be omitted. Defaults to `None`.
            references(:obj:`list`, optional): A list of
                :class:`opentracing.Reference` objects that identify one or
                more parents of type :class:`SpanContextShim`. Defaults to
                `None`.
            tags(:obj:`dict`, optional): A dictionary of tags. The keys must be
                of type :obj:`str`. The values may be one of :obj:`str`,
                :obj:`bool`, :obj:`int`, :obj:`float`. Defaults to `None`.
            start_time(:obj:`float`, optional): An explicit start time
                expressed as the number of seconds since the epoch as returned
                by :func:`time.time()`. Defaults to `None`.
            ignore_active_span(:obj:`bool`, optional): Ignore the
                currently-active span in the OpenTelemetry tracer and make the
                created span the root span of a new trace. Defaults to `False`.
            finish_on_close(:obj:`bool`, optional): Determines whether the
                created span should end automatically when closing the returned
                :class:`ScopeShim`. Defaults to `True`.

        Returns:
            A :class:`ScopeShim` that is already activated by the
            :class:`ScopeManagerShim`.
        """

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
        """Implements the ``start_span()`` method from the base class.

        Starts a span. In terms of functionality, this method behaves exactly
        like the same method on a "regular" OpenTracing tracer. See
        :meth:`opentracing.Tracer.start_span` for more details.

        Args:
            operation_name(:obj:`str`): Name of the operation represented by
                the new span from the perspective of the current service.
            child_of(:class:`SpanShim` or :class:`SpanContextShim`, optional):
                A :class:`SpanShim` or :class:`SpanContextShim` representing
                the parent in a "child of" reference. If specified, the
                *references* parameter must be omitted. Defaults to `None`.
            references(:obj:`list`, optional): A list of
                :class:`opentracing.Reference` objects that identify one or
                more parents of type :class:`SpanContextShim`. Defaults to
                `None`.
            tags(:obj:`dict`, optional): A dictionary of tags. The keys must be
                of type :obj:`str`. The values may be one of :obj:`str`,
                :obj:`bool`, :obj:`int`, :obj:`float`. Defaults to `None`.
            start_time(:obj:`float`, optional): An explicit start time
                expressed as the number of seconds since the epoch as returned
                by :func:`time.time()`. Defaults to `None`.
            ignore_active_span(:obj:`bool`, optional): Ignore the
                currently-active span in the OpenTelemetry tracer and make the
                created span the root span of a new trace. Defaults to `False`.

        Returns:
            An already-started :class:`SpanShim` instance.
        """

        # Use active span as parent when no explicit parent is specified.
        if not ignore_active_span and not child_of:
            child_of = self.active_span

        # Use the specified parent or the active span if possible. Otherwise,
        # use a `None` parent, which triggers the creation of a new trace.
        parent = child_of.unwrap() if child_of else None

        links = []
        if references:
            for ref in references:
                links.append(trace_api.Link(ref.referenced_context.unwrap()))

        # The OpenTracing API expects time values to be `float` values which
        # represent the number of seconds since the epoch. OpenTelemetry
        # represents time values as nanoseconds since the epoch.
        start_time_ns = start_time
        if start_time_ns is not None:
            start_time_ns = util.time_seconds_to_ns(start_time)

        span = self._otel_tracer.start_span(
            operation_name,
            parent,
            links=links,
            attributes=tags,
            start_time=start_time_ns,
        )

        context = SpanContextShim(span.get_context())
        return SpanShim(self, context, span)

    def inject(self, span_context, format, carrier):
        """Implements the ``inject`` method from the base class."""

        # TODO: Finish documentation.
        # pylint: disable=redefined-builtin
        # This implementation does not perform the injecting by itself but
        # uses the configured propagators in opentelemetry.propagators.
        # TODO: Support Format.BINARY once it is supported in
        # opentelemetry-python.

        if format not in self._supported_formats:
            raise opentracing.UnsupportedFormatException

        propagator = propagators.get_global_httptextformat()

        ctx = set_span_in_context(DefaultSpan(span_context.unwrap()))
        propagator.inject(type(carrier).__setitem__, carrier, context=ctx)

    def extract(self, format, carrier):
        """Implements the ``extract`` method from the base class."""

        # TODO: Finish documentation.
        # pylint: disable=redefined-builtin
        # This implementation does not perform the extracing by itself but
        # uses the configured propagators in opentelemetry.propagators.
        # TODO: Support Format.BINARY once it is supported in
        # opentelemetry-python.
        if format not in self._supported_formats:
            raise opentracing.UnsupportedFormatException

        def get_as_list(dict_object, key):
            value = dict_object.get(key)
            return [value] if value is not None else []

        propagator = propagators.get_global_httptextformat()
        ctx = propagator.extract(get_as_list, carrier)
        otel_context = get_span_from_context(ctx).get_context()

        return SpanContextShim(otel_context)
