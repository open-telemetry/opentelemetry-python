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
from flask import request
import requests

from opentelemetry import propagation, trace
from opentelemetry.distributedcontext import CorrelationContextManager
from opentelemetry.sdk.context.propagation import b3_format
from opentelemetry.sdk.trace import Tracer
from opentelemetry.sdk.trace.export import (
    BatchExportSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.baggage import BaggageManager


def configure_opentelemetry(flask_app: flask.Flask):
    trace.set_preferred_tracer_implementation(lambda T: Tracer())

    # Global initialization
    (baggage_extractor, baggage_injector) = BaggageManager.http_propagator()
    (b3_extractor, b3_injector) = b3_format.http_propagator()
    # propagation.set_http_extractors([b3_extractor, baggage_extractor])
    # propagation.set_http_injectors([b3_injector, baggage_injector])
    propagation.set_http_extractors([b3_extractor])
    propagation.set_http_injectors([b3_injector])

    # opentelemetry.ext.http_requests.enable(trace.tracer())
    # flask_app.wsgi_app = OpenTelemetryMiddleware(flask_app.wsgi_app)


def fetch_from_service_b() -> str:
    # Inject the contexts to be propagated. Note that there is no direct
    # reference to tracing or baggage.
    headers = {"Accept": "application/json"}
    propagation.inject(headers)
    print(headers)
    resp = requests.get("https://opentelemetry.io", headers=headers)
    return resp.text


def fetch_from_service_c() -> str:
    # Inject the contexts to be propagated. Note that there is no direct
    # reference to tracing or baggage.
    headers = {"Accept": "application/json"}
    propagation.inject(headers)
    print(headers)
    resp = requests.get("https://opentelemetry.io", headers=headers)
    return resp.text


app = flask.Flask(__name__)


@app.route("/")
def hello():
    tracer = trace.tracer()
    tracer.add_span_processor(BatchExportSpanProcessor(ConsoleSpanExporter()))
    with propagation.extract(request.headers):
        # extract a baggage header
        with tracer.start_as_current_span("service-span"):
            with tracer.start_as_current_span("external-req-span"):
                headers = {"Accept": "application/json"}
                propagation.inject(headers)
                version = CorrelationContextManager.value("version")
                if version == "2.0":
                    return fetch_from_service_c()

                return fetch_from_service_b()


request_headers = {
    "Accept": "application/json",
    "x-b3-traceid": "038c3fb613811e30898424c863eeae5a",
    "x-b3-spanid": "6c7f9e56212a6ffa",
    "x-b3-sampled": "0",
}

if __name__ == "__main__":
    configure_opentelemetry(app)
    app.run(debug=True)
