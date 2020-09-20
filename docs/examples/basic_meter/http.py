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
#
"""
This module shows how you can enable collection and exporting of http metrics
related to instrumentations.
"""
import requests

from opentelemetry import metrics
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter

# Sets the global MeterProvider instance
metrics.set_meter_provider(MeterProvider())

# Exporter to export metrics to the console
exporter = ConsoleMetricsExporter()

# Instrument the requests library
RequestsInstrumentor().instrument()

# Indicate to start collecting and exporting requests related metrics
metrics.get_meter_provider().start_pipeline(
    RequestsInstrumentor().meter, exporter, 5
)

response = requests.get("http://example.com")

input("...\n")
