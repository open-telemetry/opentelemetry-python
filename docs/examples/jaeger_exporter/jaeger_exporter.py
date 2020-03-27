#!/usr/bin/env python3
#
# Copyright 2020, OpenTelemetry Authors
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
from opentelemetry.ext.jaeger import JaegerSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

exporter = JaegerSpanExporter(
    service_name="my-helloworld-service",
    # configure agent
    agent_host_name="localhost",
    agent_port=6831,
    # optional: configure also collector
    # collector_host_name="localhost",
    # collector_port=14268,
    # collector_endpoint="/api/traces?format=jaeger.thrift",
    # username=xxxx, # optional
    # password=xxxx, # optional
)

span_processor = BatchExportSpanProcessor(exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

with tracer.start_as_current_span("foo"):
    with tracer.start_as_current_span("bar"):
        with tracer.start_as_current_span("baz"):
            print("Hello world from OpenTelemetry Python!")
