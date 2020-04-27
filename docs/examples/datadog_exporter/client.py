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

from sys import argv

from requests import get

from opentelemetry import propagators, trace
from opentelemetry.ext.datadog import DatadogSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

trace.set_tracer_provider(TracerProvider())

trace.get_tracer_provider().add_span_processor(
    BatchExportSpanProcessor(
        DatadogSpanExporter(
            agent_url="http://localhost:8126", service="example-client"
        )
    )
)

tracer = trace.get_tracer(__name__)

assert len(argv) == 3

with tracer.start_as_current_span("client"):

    with tracer.start_as_current_span("client-server"):
        headers = {}
        propagators.inject(dict.__setitem__, headers)
        requested = get(
            "http://localhost:8082/server_request",
            params={"param": argv[2]},
            headers=headers,
        )

        assert requested.status_code == 200
        print(requested.text)
