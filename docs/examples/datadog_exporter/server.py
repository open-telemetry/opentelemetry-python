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

from flask import Flask, request

from opentelemetry import trace
from opentelemetry.ext.datadog import DatadogExportSpanProcessor, DatadogSpanExporter
from opentelemetry.sdk.trace import TracerProvider

app = Flask(__name__)

trace.set_tracer_provider(TracerProvider())

trace.get_tracer_provider().add_span_processor(
    DatadogExportSpanProcessor(
        DatadogSpanExporter(
            agent_url="http://localhost:8126", service="example-server"
        )
    )
)

tracer = trace.get_tracer(__name__)


@app.route("/server_request")
def server_request():
    param = request.args.get("param")
    with tracer.start_as_current_span("server-inner"):
        if param == "error":
            raise ValueError("forced server error")
        return "served: {}".format(param)


if __name__ == "__main__":
    app.run(port=8082)
