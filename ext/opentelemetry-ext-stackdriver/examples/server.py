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

import flask
import requests

from opentelemetry import trace
from opentelemetry.ext import http_requests
from opentelemetry.ext.stackdriver.trace import StackdriverSpanExporter
from opentelemetry.ext.wsgi import OpenTelemetryMiddleware
from opentelemetry.sdk.trace import Tracer
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

trace.set_preferred_tracer_implementation(lambda T: Tracer())

span_processor = BatchExportSpanProcessor(StackdriverSpanExporter())
http_requests.enable(trace.tracer())
trace.tracer().add_span_processor(span_processor)

app = flask.Flask(__name__)
app.wsgi_app = OpenTelemetryMiddleware(app.wsgi_app)


@app.route("/")
def hello():
    with trace.tracer().start_as_current_span("parent"):
        requests.get("https://www.wikipedia.org/wiki/Rabbit")
    return "hello"


if __name__ == "__main__":
    app.run(debug=True)
    span_processor.shutdown()
