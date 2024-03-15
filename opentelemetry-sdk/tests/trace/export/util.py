from opentelemetry.sdk.trace import ReadableSpan, _Span
from opentelemetry.trace import SpanContext, TraceFlags


def mk_readable_span():
    ctx = SpanContext(0, 0, False)
    return ReadableSpan(context=ctx, attributes={})


def mk_spans(n):
    span = mk_span('foo')
    out = []
    for _ in range(n):
        out.append(span)
    return out


def create_start_and_end_span(name, span_processor):
    span = _Span(name, mk_ctx(), span_processor=span_processor)
    span.start()
    span.end()


def mk_span(name):
    return _Span(name=name, context=mk_ctx())


def mk_ctx():
    return SpanContext(1, 2, False, trace_flags=TraceFlags(TraceFlags.SAMPLED))
