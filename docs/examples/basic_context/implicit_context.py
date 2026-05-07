# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import baggage, trace
from opentelemetry.sdk.trace import TracerProvider

trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

with tracer.start_span(name="root span") as root_span:
    ctx = baggage.set_baggage("foo", "bar")

print(f"Global context baggage: {baggage.get_all()}")
print(f"Span context baggage: {baggage.get_all(context=ctx)}")
