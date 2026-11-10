# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import trace
from opentelemetry.trace import SpanKind

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("health", kind=SpanKind.SERVER, attributes={"route": "/health"}):
    pass
with tracer.start_as_current_span("api", attributes={"route": "/api/users"}):
    with tracer.start_as_current_span("child"):
        pass
with tracer.start_as_current_span("api-internal", attributes={"route": "/api/internal/x"}):
    pass
with tracer.start_as_current_span("server", kind=SpanKind.SERVER):
    pass
with tracer.start_as_current_span("other"):
    pass
