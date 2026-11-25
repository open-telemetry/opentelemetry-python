# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Two text map propagators that stand in for a real one in tests.

:class:`NOOPTextMapPropagator` carries nothing, so it exercises the path where
extraction yields no span context. :class:`MockTextMapPropagator` carries the
trace id and span id as decimal strings under two keys of its own, so a test can
assert on the exact carrier contents without having to parse the W3C
``traceparent`` format.

Neither is a valid propagator to use outside a test: the format of
:class:`MockTextMapPropagator` is not interoperable with anything, and
:class:`NOOPTextMapPropagator` loses context silently.
"""

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.propagators.textmap import (
    CarrierT,
    Getter,
    Setter,
    TextMapPropagator,
    default_getter,
    default_setter,
)


class NOOPTextMapPropagator(TextMapPropagator):
    """A propagator that does not extract nor inject.

    This class is useful for catching edge cases assuming
    a SpanContext will always be present.
    """

    def extract(
        self,
        carrier: CarrierT,
        context: Context | None = None,
        getter: Getter = default_getter,
    ) -> Context:
        """Return an empty context, reading nothing from the carrier.

        Args:
            carrier: Ignored. Nothing is read from it.
            context: Ignored. The context passed in is discarded rather than
                returned, so any baggage or span it carried is lost.
            getter: Ignored, since the carrier is never read.

        Returns:
            A new empty ``Context``. A span started from it has no parent, which
            is the case this propagator exists to produce.
        """
        return Context()

    def inject(
        self,
        carrier: CarrierT,
        context: Context | None = None,
        setter: Setter = default_setter,
    ) -> None:
        """Write nothing to the carrier.

        Args:
            carrier: Left unchanged.
            context: Ignored.
            setter: Ignored, since the carrier is never written.
        """

    @property
    def fields(self):
        """Return the carrier keys this propagator writes.

        Returns:
            An empty set, since ``inject`` writes nothing. A framework that
            clears these keys before injecting therefore clears nothing.
        """
        return set()


class MockTextMapPropagator(TextMapPropagator):
    """Mock propagator for testing purposes.

    Carries the trace id and the span id as decimal strings under the
    ``mock-traceid`` and ``mock-spanid`` keys. Trace flags, trace state and
    baggage are not carried, so a span extracted from a carrier this propagator
    wrote is never sampled through the propagated flags.
    """

    TRACE_ID_KEY = "mock-traceid"
    SPAN_ID_KEY = "mock-spanid"

    def extract(
        self,
        carrier: CarrierT,
        context: Context | None = None,
        getter: Getter = default_getter,
    ) -> Context:
        """Read the trace id and span id from the carrier into a span context.

        Args:
            carrier: The carrier to read ``mock-traceid`` and ``mock-spanid``
                from. Only the first value of each is used when the getter
                returns several.
            context: Context to extract into. ``None`` means a new empty
                ``Context``.
            getter: Reads the two keys out of the carrier.

        Returns:
            A context whose current span is a ``NonRecordingSpan`` with the
            trace id and span id from the carrier, marked remote. When either
            key is missing or empty, the context is returned unchanged, so the
            caller cannot distinguish that from a carrier that was never
            written to.

        Raises:
            ValueError: When either value is present but is not a decimal
                integer. A real propagator reports a malformed carrier by
                returning the context unchanged instead.
        """
        if context is None:
            context = Context()
        trace_id_list = getter.get(carrier, self.TRACE_ID_KEY)
        span_id_list = getter.get(carrier, self.SPAN_ID_KEY)

        if not trace_id_list or not span_id_list:
            return context

        return trace.set_span_in_context(
            trace.NonRecordingSpan(
                trace.SpanContext(
                    trace_id=int(trace_id_list[0]),
                    span_id=int(span_id_list[0]),
                    is_remote=True,
                )
            ),
            context,
        )

    def inject(
        self,
        carrier: CarrierT,
        context: Context | None = None,
        setter: Setter = default_setter,
    ) -> None:
        """Write the trace id and span id of the current span to the carrier.

        Both are written as decimal strings. No check is made that the span
        context is valid, so an invalid context is written out as two zeros
        rather than skipped, which is how a test can tell that injection
        happened with no span in context.

        Args:
            carrier: The carrier to write the two keys into.
            context: Context to read the current span from. ``None`` means the
                current context.
            setter: Writes the two keys into the carrier.
        """
        span = trace.get_current_span(context)
        setter.set(carrier, self.TRACE_ID_KEY, str(span.get_span_context().trace_id))
        setter.set(carrier, self.SPAN_ID_KEY, str(span.get_span_context().span_id))

    @property
    def fields(self):
        """Return the carrier keys this propagator writes.

        Returns:
            A set holding ``mock-traceid`` and ``mock-spanid``. A framework
            reusing a carrier clears these before injecting.
        """
        return {self.TRACE_ID_KEY, self.SPAN_ID_KEY}
