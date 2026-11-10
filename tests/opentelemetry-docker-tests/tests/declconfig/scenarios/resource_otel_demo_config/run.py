# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import metrics, trace
from opentelemetry._logs import get_logger

with trace.get_tracer(__name__).start_as_current_span("demo-span"):
    metrics.get_meter(__name__).create_counter("demo.requests").add(1)
    get_logger(__name__).emit(body="demo log")
