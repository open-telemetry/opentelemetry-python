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
import flask
import requests

import opentelemetry.ext.http_requests
from opentelemetry import propagators, trace
from opentelemetry import baggage
from opnetelemetry.context import Context
from opentelemetry.ext.wsgi import OpenTelemetryMiddleware
from opentelemetry.sdk.context.propagation.b3_format import B3Format
from opentelemetry.sdk.trace import Tracer


def configure_opentelemetry(flask_app: flask.Flask):
    """Configure a flask application to use OpenTelemetry.

    This activates the specific components:

    * sets tracer to the SDK's Tracer
    * enables requests integration on the Tracer
    * uses a WSGI middleware to enable configuration

    TODO:

    * processors?
    * exporters?
    """
    # Start by configuring all objects required to ensure
    # a complete end to end workflow.
    # the preferred implementation of these objects must be set,
    # as the opentelemetry-api defines the interface with a no-op
    # implementation.
    trace.set_preferred_tracer_implementation(lambda _: Tracer())
    # extractors and injectors are now separate, as it could be possible
    # to want different behavior for those (e.g. don't propagate because of external services)
    #
    # the current configuration will only propagate w3c/correlationcontext
    # and baggage. One would have to add other propagators to handle
    # things such as w3c/tracecontext
    propagator_list = [CorrelationContextFormat(), BaggageFormat()]

    propagators.set_http_extractors(propagator_list)
    propagators.set_http_injectors(propagator_list)

    # Integrations are the glue that binds the OpenTelemetry API
    # and the frameworks and libraries that are used together, automatically
    # creating Spans and propagating context as appropriate.
    opentelemetry.ext.http_requests.enable(trace.tracer())
    flask_app.wsgi_app = OpenTelemetryMiddleware(flask_app.wsgi_app)


app = flask.Flask(__name__)


@app.route("/")
def hello():
    # extract a baggage header
    original_service = baggage.get(Context, "original-service")
    # add a new one
    baggage.set(Context, "environment", "foo")
    return "hello"


configure_opentelemetry(app)
