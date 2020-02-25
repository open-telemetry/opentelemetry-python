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

import requests

from opentelemetry import trace
from opentelemetry.ext import http_requests
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchExportSpanProcessor,
    ConsoleSpanExporter,
)

if os.getenv("EXPORTER") == "jaeger":
    from opentelemetry.ext.jaeger import JaegerSpanExporter

    exporter = JaegerSpanExporter(
        service_name="http-client",
        agent_host_name="localhost",
        agent_port=6831,
    )
else:
    exporter = ConsoleSpanExporter()

# The preferred tracer implementation must be set, as the opentelemetry-api
# defines the interface with a no-op implementation.
trace.set_preferred_tracer_provider_implementation(lambda T: TracerProvider())
tracer_provider = trace.tracer_provider()

# SpanExporter receives the spans and send them to the target location.
span_processor = BatchExportSpanProcessor(exporter)
tracer_provider.add_span_processor(span_processor)

# Integrations are the glue that binds the OpenTelemetry API and the
# frameworks and libraries that are used together, automatically creating
# Spans and propagating context as appropriate.
http_requests.enable(tracer_provider)
response = requests.get(url="http://127.0.0.1:5000/")
