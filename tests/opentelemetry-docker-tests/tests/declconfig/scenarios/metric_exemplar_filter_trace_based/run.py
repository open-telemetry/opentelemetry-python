# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import metrics, trace

meter = metrics.get_meter(__name__)
inside = meter.create_counter("inside.requests")
outside = meter.create_counter("outside.requests")

with trace.get_tracer(__name__).start_as_current_span("exemplar-span"):
    inside.add(1)
outside.add(1)
