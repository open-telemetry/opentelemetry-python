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
This module serves as an example for a simple application using metrics
"""

from opentelemetry import metrics
from opentelemetry.sdk.metrics import Meter


metrics.set_preferred_meter_implementation(lambda _: Meter())
METER = metrics.meter()
COUNTER = METER.create_counter(
    "sum numbers",
    "sum numbers over time",
    "number",
    int,
    False,
    ["environment"],
)

counter_handle = COUNTER.get_handle("Staging")

for i in range(100):
    counter_handle.add(i)

print(counter_handle.data)

# TODO: exporters
