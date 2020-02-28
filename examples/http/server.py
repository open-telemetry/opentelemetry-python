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

import flask
import requests

from opentelemetry import trace
from opentelemetry.ext import http_requests
from opentelemetry.ext.wsgi import OpenTelemetryMiddleware
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleExportSpanProcessor,
)

if os.getenv("EXPORTER") == "jaeger":
    from opentelemetry.ext.jaeger import JaegerSpanExporter

    exporter = JaegerSpanExporter(
        service_name="http-server",
        agent_host_name="localhost",
        agent_port=6831,
    )
else:
    exporter = ConsoleSpanExporter()

# The preferred tracer implementation must be set, as the opentelemetry-api
# defines the interface with a no-op implementation.
trace.set_preferred_tracer_provider_implementation(lambda T: TracerProvider())
tracer = trace.get_tracer(__name__)

# SpanExporter receives the spans and send them to the target location.
span_processor = SimpleExportSpanProcessor(exporter)
trace.tracer_provider().add_span_processor(span_processor)

# Integrations are the glue that binds the OpenTelemetry API and the
# frameworks and libraries that are used together, automatically creating
# Spans and propagating context as appropriate.
http_requests.enable(trace.tracer_provider())
app = flask.Flask(__name__)
app.wsgi_app = OpenTelemetryMiddleware(app.wsgi_app)


@app.route("/")
def hello():
    with tracer.start_as_current_span("parent"):
        requests.get("https://www.wikipedia.org/wiki/Rabbit")
    return "hello"


if __name__ == "__main__":
    app.run(debug=True)
