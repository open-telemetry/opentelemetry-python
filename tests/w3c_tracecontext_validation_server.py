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
"""
This server is intended to be used with the W3C tracecontext validation
Service. It implements the APIs needed to be exercised by the test bed.
"""

import json

import flask
import requests

from opentelemetry import trace
from opentelemetry.ext import http_requests
from opentelemetry.ext.wsgi import OpenTelemetryMiddleware
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleExportSpanProcessor,
)

# Integrations are the glue that binds the OpenTelemetry API and the
# frameworks and libraries that are used together, automatically creating
# Spans and propagating context as appropriate.
http_requests.enable(trace.get_tracer_provider())

# SpanExporter receives the spans and send them to the target location.
span_processor = SimpleExportSpanProcessor(ConsoleSpanExporter())
trace.get_tracer_provider().add_span_processor(span_processor)

app = flask.Flask(__name__)
app.wsgi_app = OpenTelemetryMiddleware(app.wsgi_app)


@app.route("/verify-tracecontext", methods=["POST"])
def verify_tracecontext():
    """Upon reception of some payload, sends a request back to the designated
    url.

    This route is designed to be testable with the w3c tracecontext server /
    client test.
    """
    for action in flask.request.json:
        requests.post(
            url=action["url"],
            data=json.dumps(action["arguments"]),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json; charset=utf-8",
            },
            timeout=5.0,
        )
    return "hello"


if __name__ == "__main__":
    try:
        app.run(debug=True)
    finally:
        span_processor.shutdown()
