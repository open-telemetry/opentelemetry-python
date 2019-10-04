#!/usr/bin/env python3
#
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
from opentelemetry.sdk.trace import Tracer
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleExportSpanProcessor,
)

# The preferred tracer implementation must be set, as the opentelemetry-api
# defines the interface with a no-op implementation.
trace.set_preferred_tracer_implementation(lambda T: Tracer())
tracer = trace.tracer()

# Integrations are the glue that binds the OpenTelemetry API and the
# frameworks and libraries that are used together, automatically creating
# Spans and propagating context as appropriate.
http_requests.enable(tracer)

# SpanExporter receives the spans and send them to the target location.
span_processor = SimpleExportSpanProcessor(ConsoleSpanExporter())
tracer.add_span_processor(span_processor)

response = requests.get(url="http://127.0.0.1:5000/")
span_processor.shutdown()
