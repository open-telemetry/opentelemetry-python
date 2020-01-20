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
#
"""
This module serves as an example for baggage, which exists
to pass application-defined key-value pairs from service to service.
"""
# import opentelemetry.ext.http_requests
# from opentelemetry.ext.wsgi import OpenTelemetryMiddleware

import flask
import requests
from flask import request

import opentelemetry.ext.http_requests
from opentelemetry import propagation, trace
from opentelemetry.correlationcontext import CorrelationContextManager
from opentelemetry.ext.wsgi import OpenTelemetryMiddleware
from opentelemetry.sdk.context.propagation import b3_format
from opentelemetry.sdk.trace import TracerSource
from opentelemetry.sdk.trace.export import (
    BatchExportSpanProcessor,
    ConsoleSpanExporter,
)


def configure_opentelemetry(flask_app: flask.Flask):
    trace.set_preferred_tracer_source_implementation(lambda T: TracerSource())
    trace.tracer_source().add_span_processor(
        BatchExportSpanProcessor(ConsoleSpanExporter())
    )

    # Global initialization
    (b3_extractor, b3_injector) = b3_format.http_propagator()
    # propagation.set_http_extractors([b3_extractor, baggage_extractor])
    # propagation.set_http_injectors([b3_injector, baggage_injector])
    propagation.set_http_extractors([b3_extractor])
    propagation.set_http_injectors([b3_injector])

    opentelemetry.ext.http_requests.enable(trace.tracer_source())
    flask_app.wsgi_app = OpenTelemetryMiddleware(flask_app.wsgi_app)


def fetch_from_service_b() -> str:
    with trace.tracer_source().get_tracer(__name__).start_as_current_span(
        "fetch_from_service_b"
    ):
        # Inject the contexts to be propagated. Note that there is no direct
        # reference to tracing or baggage.
        headers = {"Accept": "text/html"}
        propagation.inject(headers)
        resp = requests.get("https://opentelemetry.io", headers=headers)
        return resp.text


def fetch_from_service_c() -> str:
    with trace.tracer_source().get_tracer(__name__).start_as_current_span(
        "fetch_from_service_c"
    ):
        # Inject the contexts to be propagated. Note that there is no direct
        # reference to tracing or baggage.
        headers = {"Accept": "application/json"}
        propagation.inject(headers)
        resp = requests.get("https://opentelemetry.io", headers=headers)
        return resp.text


app = flask.Flask(__name__)


@app.route("/")
def hello():
    tracer = trace.tracer_source().get_tracer(__name__)
    # extract a baggage header
    propagation.extract(request.headers)

    with tracer.start_as_current_span("service-span"):
        with tracer.start_as_current_span("external-req-span"):
            version = CorrelationContextManager.correlation("version")
            if version == "2.0":
                return fetch_from_service_c()
            return fetch_from_service_b()


if __name__ == "__main__":
    configure_opentelemetry(app)
    app.run(debug=True)
