# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import trace

print(f"tracer_provider={type(trace.get_tracer_provider()).__name__}")

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("error-span"):
    pass
