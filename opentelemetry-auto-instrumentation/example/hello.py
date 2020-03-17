# Copyright 2020, OpenTelemetry Authors
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

from flask import Flask
from requests import get

from opentelemetry import propagators, trace
from opentelemetry.context.propagation.tracecontexthttptextformat import (
    TraceContextHTTPTextFormat,
)
from opentelemetry.propagators import set_global_httptextformat
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleExportSpanProcessor,
)

app = Flask(__name__)

trace.set_preferred_tracer_provider_implementation(lambda T: TracerProvider())
tracer = trace.tracer_provider().get_tracer(__name__)

trace.tracer_provider().add_span_processor(
    SimpleExportSpanProcessor(ConsoleSpanExporter())
)
set_global_httptextformat(TraceContextHTTPTextFormat)


def http_get(port, path, param, value):

    headers = {}
    propagators.inject(tracer, dict.__setitem__, headers)

    requested = get(
        "http://localhost:{}/{}".format(port, path),
        params={param: value},
        headers=headers,
    )

    assert requested.status_code == 200
    return requested.text


assert len(argv) == 2

hello_to = argv[1]

with tracer.start_as_current_span("hello") as hello_span:

    with tracer.start_as_current_span("hello-format", parent=hello_span):
        hello_str = http_get(8081, "format_request", "helloTo", hello_to)

    with tracer.start_as_current_span("hello-publish", parent=hello_span):
        http_get(8082, "publish_request", "helloStr", hello_str)
