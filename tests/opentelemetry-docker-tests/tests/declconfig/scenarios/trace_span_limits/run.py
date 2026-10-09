# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import trace
from opentelemetry.trace import Link

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("target") as target:
    pass

# Once a count limit is reached, the oldest attribute or link is dropped.
links = [
    Link(target.get_span_context(), {"z": 3}),
    Link(target.get_span_context(), {"x": 1, "y": 2}),
]
with tracer.start_as_current_span("limited-span", attributes={"dropped": 0, "a": "abcdefgh", "b": 1}, links=links):
    pass
