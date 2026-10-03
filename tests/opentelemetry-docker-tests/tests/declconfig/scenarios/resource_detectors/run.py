# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("detected-span"):
    pass
