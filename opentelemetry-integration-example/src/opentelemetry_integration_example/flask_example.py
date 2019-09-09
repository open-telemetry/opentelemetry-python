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
import flask
import requests
from opentelemetry import trace
import opentelemetry.ext.http_requests
from opentelemetry.sdk.trace import Tracer
from opentelemetry.ext.wsgi import OpenTelemetryMiddleware


def configure_opentelemetry(app: flask.Flask):
    """Configure a flask application to use OpenTelemetry.

    This activates the specific components:

    * sets tracer to the SDK's Tracer
    * enables requests integration on the Tracer
    * uses a WSGI middleware to enable configuration

    TODO:

    * exporters?
    * configure propagators / formatters
    """
    # Start by configuring all objects required to ensure
    # a complete end to end workflow.
    # the preferred implementation of these objects must be set,
    # as the opentelemetry-api defines the interface, but not
    # the implementation.
    trace.set_preferred_tracer_implementation(lambda T: Tracer())
    # Integrations are the glue that binds the opentelemetry API
    # and the frameworks and libraries that are used, injecting
    # context propagation and the appropriate span tags
    # from said frameworks and libraries.
    opentelemetry.ext.http_requests.enable(trace.tracer())
    app.wsgi_app = OpenTelemetryMiddleware(app.wsgi_app)


app = flask.Flask(__name__)


@app.route("/")
def hello():
    return "hello"


configure_opentelemetry(app)
