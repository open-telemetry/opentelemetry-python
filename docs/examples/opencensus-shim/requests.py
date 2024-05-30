# Copyright The OpenTelemetry Authors
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

from flask import Flask
import requests
from opencensus.ext.flask.flask_middleware import FlaskMiddleware
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.shim.opencensus import install_shim
from opencensus.trace import config_integration


# Set up OpenTelemetry
resource = Resource(attributes={
    "service.name": "opencensus-shim-requests-example"
})
tracer_provider = TracerProvider(resource=resource)
trace.set_tracer_provider(tracer_provider)

# Configure OTel to export traces to the console
span_processor = BatchSpanProcessor(ConsoleSpanExporter())
tracer_provider.add_span_processor(span_processor)
tracer = tracer_provider.get_tracer(__name__)

# Install the shim to start bridging spans from OpenCensus to OpenTelemetry
install_shim()

# Setup Flask with OpenCensus instrumentation
app = Flask(__name__)
FlaskMiddleware(app)

config_integration.trace_integrations(['requests'])


@app.route("/")
def endpoint():
    with tracer.start_as_current_span("Parent"):
        response = requests.get("http://example.com")  # Example external request
    return f"Hello, World! External request status: {response.status_code}"

if __name__ == "__main__":
    app.run(port=8080)
