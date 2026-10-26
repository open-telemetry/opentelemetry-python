# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import baggage, propagate, trace

tracer = trace.get_tracer(__name__)

incoming = {
    "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
    "baggage": "user.id=u-123",
}
extracted = propagate.extract(incoming)
print(f"remote_span_valid={trace.get_current_span(extracted).get_span_context().is_valid}")
print(f"baggage.user.id={baggage.get_baggage('user.id', extracted) or '<none>'}")

with tracer.start_as_current_span("disabled-span", context=extracted):
    pass
