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
This module serves as an example to integrate with flask, using
the requests library to perform downstream requests
"""
import time

import flask

import opentelemetry.ext.http_requests
from opentelemetry import trace
from opentelemetry.ext.wsgi import OpenTelemetryMiddleware
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
    * propagators?
    """
    # Start by configuring all objects required to ensure
    # a complete end to end workflow.
    # the preferred implementation of these objects must be set,
    # as the opentelemetry-api defines the interface with a no-op
    # implementation.
    trace.set_preferred_tracer_implementation(lambda _: Tracer())
    # Integrations are the glue that binds the OpenTelemetry API
    # and the frameworks and libraries that are used together, automatically
    # creating Spans and propagating context as appropriate.
    opentelemetry.ext.http_requests.enable(trace.tracer())
    flask_app.wsgi_app = OpenTelemetryMiddleware(flask_app.wsgi_app)


app = flask.Flask(__name__)


@app.route("/")
def hello():
    # emit a trace that measures how long the
    # sleep takes
    with trace.tracer().start_span("sleep"):
        time.sleep(0.001)
    return "hello"


configure_opentelemetry(app)
