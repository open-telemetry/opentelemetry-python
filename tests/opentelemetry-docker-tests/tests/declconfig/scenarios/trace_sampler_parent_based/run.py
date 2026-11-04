# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import trace
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags

tracer = trace.get_tracer(__name__)


def parent_context(sampled: bool, remote: bool):
    span_context = SpanContext(
        trace_id=0x0AF7651916CD43DD8448EB211C80319C,
        span_id=0xB7AD6B7169203331,
        is_remote=remote,
        trace_flags=TraceFlags(TraceFlags.SAMPLED if sampled else TraceFlags.DEFAULT),
    )
    return trace.set_span_in_context(NonRecordingSpan(span_context))


with tracer.start_as_current_span("root"):
    with tracer.start_as_current_span("local-sampled-child"):
        pass

for name, sampled, remote in [
    ("local-unsampled-child", False, False),
    ("remote-sampled-child", True, True),
    ("remote-unsampled-child", False, True),
]:
    with tracer.start_as_current_span(name, context=parent_context(sampled, remote)):
        pass
