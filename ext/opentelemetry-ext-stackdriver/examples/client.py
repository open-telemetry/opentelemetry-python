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

import requests

from opentelemetry import trace
from opentelemetry.ext import http_requests
from opentelemetry.ext.stackdriver.trace import StackdriverSpanExporter
from opentelemetry.sdk.trace import Tracer
from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor

trace.set_preferred_tracer_implementation(lambda T: Tracer())
tracer = trace.tracer()
span_processor = SimpleExportSpanProcessor(
    StackdriverSpanExporter(project_id="my-helloworld-project")
)
tracer.add_span_processor(span_processor)

http_requests.enable(tracer)
response = requests.get(url="http://localhost:7777/hello")
span_processor.shutdown()
