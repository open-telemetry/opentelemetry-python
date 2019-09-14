import opentelemetry.trace as trace
from opentelemetry.context.propagation import httptextformat


class TraceStateHTTPTextFormat(httptextformat.HTTPTextFormat):
    """TODO: a propagator that extracts and injects tracestate.
    """

    def extract(
        self, _get_from_carrier: httptextformat.Getter, _carrier: object
    ) -> trace.SpanContext:
        return trace.INVALID_SPAN_CONTEXT

    def inject(
        self,
        context: trace.SpanContext,
        set_in_carrier: httptextformat.Setter,
        carrier: object,
    ) -> None:
        pass
