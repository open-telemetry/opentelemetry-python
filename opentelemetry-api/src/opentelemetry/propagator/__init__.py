import typing

import opentelemetry.context.propagation.httptextformat as httptextformat
import opentelemetry.trace as trace
from opentelemetry.context.propagation.tracestatehttptextformat import (
    TraceStateHTTPTextFormat,
)


class Propagator:
    """Class which encapsulates propagation of values to and from context.

    In contrast to using the formatters directly, a propagator object can
    help own configuration around which formatters to use, as well as
    help simplify the work require for integrations to use the intended
    formatters.
    """

    def __init__(self, httptextformat_instance: httptextformat.HTTPTextFormat):
        self._httptextformat = httptextformat_instance

    def extract(
        self, get_from_carrier: httptextformat.Getter, carrier: object
    ) -> typing.Union[trace.SpanContext, trace.Span, None]:
        """Load the parent SpanContext from values in the carrier.

        Using the specified HTTPTextFormatter, the propagator will
        extract a SpanContext from the carrier. If one is found,
        it will be set as the parent context of the current span.

        Args:
            get_from_carrier: a function that can retrieve zero
                or more values from the carrier. In the case that
                the value does not exist, return an empty list.
            carrier: and object which contains values that are
                used to construct a SpanContext. This object
                must be paired with an appropriate get_from_carrier
                which understands how to extract a value from it.
        """
        span_context = self._httptextformat.extract(get_from_carrier, carrier)
        return span_context if span_context else trace.Tracer.CURRENT_SPAN

    def inject(
        self,
        tracer: trace.Tracer,
        set_in_carrier: httptextformat.Setter,
        carrier: object,
    ) -> None:
        """Inject values from the current context into the carrier.

        inject enables the propagation of values into HTTP clients or
        other objects which perform an HTTP request. Implementations
        should use the set_in_carrier method to set values on the
        carrier.

        Args:
            set_in_carrier: A setter function that can set values
                on the carrier.
            carrier: An object that a place to define HTTP headers.
                Should be paired with set_in_carrier, which should
                know how to set header values on the carrier.
        """
        self._httptextformat.inject(
            tracer.get_current_span().get_context(), set_in_carrier, carrier
        )


_PROPAGATOR = Propagator(TraceStateHTTPTextFormat())


def get_global_propagator() -> Propagator:
    return _PROPAGATOR


def set_global_propagator(propagator: Propagator) -> None:
    global _PROPAGATOR  # pylint:disable=global-statement
    _PROPAGATOR = propagator
