# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import sys

from requests import get

from opentelemetry import trace
from opentelemetry.propagate import inject
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)

trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer_provider().get_tracer(__name__)

trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(ConsoleSpanExporter())
)

# Get parameter from command line argument or use default value "testing"
param_value = sys.argv[1] if len(sys.argv) > 1 else "testing"

with tracer.start_as_current_span("client"):
    with tracer.start_as_current_span("client-server"):
        headers = {}
        inject(headers)
        requested = get(
            "http://localhost:8082/server_request",
            params={"param": param_value},
            headers=headers,
        )

        assert requested.status_code == 200
