#!/usr/bin/env python3
#
# Copyright 2019, OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.sdk.trace import Tracer
from opentelemetry.sdk.trace.export import (
    BatchExportSpanProcessor,
    ConsoleSpanExporter,
)

if os.getenv("EXPORTER") == "jaeger":
    from opentelemetry.ext.jaeger import JaegerSpanExporter

    exporter = JaegerSpanExporter(
        service_name="basic-service",
        agent_host_name="localhost",
        agent_port=6831,
    )
else:
    exporter = ConsoleSpanExporter()

# The preferred tracer implementation must be set, as the opentelemetry-api
# defines the interface with a no-op implementation.
trace.set_preferred_tracer_implementation(lambda T: Tracer())
tracer = trace.tracer()

# SpanExporter receives the spans and send them to the target location.
span_processor = BatchExportSpanProcessor(exporter)

tracer.add_span_processor(span_processor)
with tracer.start_as_current_span("foo"):
    with tracer.start_as_current_span("bar"):
        with tracer.start_as_current_span("baz"):
            print(Context)

