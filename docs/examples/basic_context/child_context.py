# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import baggage, trace

tracer = trace.get_tracer(__name__)

global_ctx = baggage.set_baggage("context", "global")
with tracer.start_as_current_span(name="root span") as root_span:
    parent_ctx = baggage.set_baggage("context", "parent")
    with tracer.start_as_current_span(
        name="child span", context=parent_ctx
    ) as child_span:
        child_ctx = baggage.set_baggage("context", "child")

print(baggage.get_baggage("context", global_ctx))
print(baggage.get_baggage("context", parent_ctx))
print(baggage.get_baggage("context", child_ctx))
