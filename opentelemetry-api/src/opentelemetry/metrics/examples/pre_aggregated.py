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

# pylint: skip-file
from opentelemetry import metrics

METER = metrics.Meter()
COUNTER = METER.create_int_counter(
    "sum numbers",
    "sum numbers over time",
    "number",
    metrics.ValueType.FLOAT,
    ["environment"],
)

# Metrics sent to some exporter
METRIC_TESTING = COUNTER.get_or_create_time_series("Testing")
METRIC_STAGING = COUNTER.get_or_create_time_series("Staging")

for i in range(100):
    METRIC_STAGING.add(i)
