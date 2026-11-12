# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import trace
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags

tracer = trace.get_tracer(__name__)

# The root sampler drops this span, always_record turns that into RECORD_ONLY,
# so the span records but is not sampled and never reaches the exporter.
with tracer.start_as_current_span("record-only-root") as span:
    print(
        f"record-only-root recording={span.is_recording()} sampled={span.get_span_context().trace_flags.sampled}",
        flush=True,
    )

sampled_parent = SpanContext(
    trace_id=0x0AF7651916CD43DD8448EB211C80319C,
    span_id=0xB7AD6B7169203331,
    is_remote=True,
    trace_flags=TraceFlags(TraceFlags.SAMPLED),
)
with tracer.start_as_current_span(
    "sampled-remote-child",
    context=trace.set_span_in_context(NonRecordingSpan(sampled_parent)),
):
    pass
