# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import _logs, metrics, trace

print(f"meter_provider={type(metrics.get_meter_provider()).__name__}")
print(f"logger_provider={type(_logs.get_logger_provider()).__name__}")

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("omitted-providers-span"):
    pass
