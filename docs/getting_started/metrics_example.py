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

# metrics.py
# This is still work in progress as the metrics SDK is being implemented

from opentelemetry._metrics import get_meter_provider, set_meter_provider
from opentelemetry.sdk._metrics import MeterProvider
from opentelemetry.sdk._metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)

exporter = ConsoleMetricExporter()
reader = PeriodicExportingMetricReader(exporter)
provider = MeterProvider(metric_readers=[reader])
set_meter_provider(provider)

meter = get_meter_provider().get_meter("getting-started")
counter = meter.create_counter("first_counter")
counter.add(1)
# TODO: fill in details for additional metrics
