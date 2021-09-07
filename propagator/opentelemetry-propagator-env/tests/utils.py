import opentelemetry
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace.span import NonRecordingSpan
from opentelemetry.trace.span import SpanContext
from opentelemetry.trace.span import format_span_id
from opentelemetry.trace.span import format_trace_id
from opentelemetry.baggage import _BAGGAGE_KEY
from opentelemetry.context import get_value, set_value


def create_dummy_context():
    trace_id = 0x546a43e10e63d462df190eb91fccd21c
    span_id = 0xa61596de7d07c857
    sampled = "0"
    return opentelemetry.trace.propagation.set_span_in_context(
        NonRecordingSpan(
            SpanContext(
                trace_id=trace_id,
                span_id=span_id,
                is_remote=True,
                trace_flags=trace.TraceFlags(0),
                trace_state=trace.TraceState(),
            )
        ),
        {}
    )

def create_dummy_context2():
    trace_id = 0x899a43e10e63d462df190eb91fccd21c
    span_id = 0xa89996de7d07c857
    sampled = "1"
    return opentelemetry.trace.propagation.set_span_in_context(
        NonRecordingSpan(
            SpanContext(
                trace_id=trace_id,
                span_id=span_id,
                is_remote=True,
                trace_flags=trace.TraceFlags(0),
                trace_state=trace.TraceState(),
            )
        ),
        {}
    )

def create_dummy_context3():
    trace_id = 0x899a43e10e63d462
    span_id = 0xa89996de7d07c857
    sampled = "1"
    return opentelemetry.trace.propagation.set_span_in_context(
        NonRecordingSpan(
            SpanContext(
                trace_id=trace_id,
                span_id=span_id,
                is_remote=True,
                trace_flags=trace.TraceFlags(0),
                trace_state=trace.TraceState(),
            )
        ),
        {}
    )

def create_dummy_context_with_parent_span():
    trace_id = 0x546a43e10e63d462df190eb91fccd21c
    span_id = 0xa61596de7d07c857
    sampled = "0"
    default_span = NonRecordingSpan(
            SpanContext(
                trace_id=trace_id,
                span_id=span_id,
                is_remote=True,
                trace_flags=trace.TraceFlags(0),
                trace_state=trace.TraceState(),
            )
        )
    setattr(default_span, "parent", SpanContext(trace_id = trace_id, span_id = 0xca6f04b3f3de0b3d, is_remote = True))
    return opentelemetry.trace.propagation.set_span_in_context(default_span, {})


def create_invalid_context():
    INVALID_SPAN_ID = 0x0000000000000000
    INVALID_TRACE_ID = 0x00000000000000000000000000000000
    sampled = "0"
    INVALID_SPAN_CONTEXT = SpanContext(
    trace_id=INVALID_TRACE_ID,
    span_id=INVALID_SPAN_ID,
    is_remote=False,
    trace_flags=trace.TraceFlags(0),
    trace_state=trace.TraceState(),
    )
    INVALID_SPAN = NonRecordingSpan(INVALID_SPAN_CONTEXT)
    return opentelemetry.trace.propagation.set_span_in_context(INVALID_SPAN, {})

def create_invalid_context_with_baggage():
    dummy_context = create_invalid_context()
    return set_value(_BAGGAGE_KEY, {"test1":1, "test2":2}, context=dummy_context)

def create_valid_context_with_baggage():
    dummy_context = create_dummy_context()
    return set_value(_BAGGAGE_KEY, {"key1":1, "key2":2}, context=dummy_context)

def create_valid_context_with_baggage2():
    dummy_context = create_dummy_context2()
    return set_value(_BAGGAGE_KEY, {"key3":1, "key4":2}, context=dummy_context)


def get_details_from_context(context):
    span = trace.get_current_span(context)
    if span is None:
        return span
    span_parent = getattr(span, "parent", None)
    span_context = span.get_span_context()
    trace_id = format_trace_id(span_context.trace_id)
    span_id = format_span_id(span_context.span_id)
    sampled = span_context.trace_flags
    tracestate = span_context.trace_state
    if span_parent:
        parent_span_id = format_span_id(span_parent.span_id)
    else:
        parent_span_id = None
    return trace_id, span_id, sampled, parent_span_id, tracestate
