# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import trace

tracer = trace.get_tracer(__name__)

for _ in range(10):
    with tracer.start_as_current_span("never", attributes={"sample": "never"}):
        pass
for index in range(10):
    with tracer.start_as_current_span("always", attributes={"sample": "always"}):
        if index == 0:
            with tracer.start_as_current_span("threshold-child"):
                pass
with tracer.start_as_current_span("threshold-root"):
    pass
