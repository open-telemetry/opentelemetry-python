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

from opentelemetry.metrics import LabelKey
from opentelemetry.metrics import LabelValue
from opentelemetry.metrics import Meter
from opentelemetry.metrics import MeasureBatch
from opentelemetry.metrics.aggregation import LastValueAggregation

METER = Meter()
LABEL_KEYS = [LabelKey("environment",
                       "the environment the application is running in")]
MEASURE = METER.create_float_measure("idle_cpu_percentage",  # pragma: no cover
                                     "cpu idle over time",
                                     "percentage",
                                     LABEL_KEYS,
                                     LastValueAggregation)
LABEL_VALUE_TESTING = [LabelValue("Testing")]
LABEL_VALUE_STAGING = [LabelValue("Staging")]

# Metrics sent to some exporter
MEASURE_METRIC_TESTING = MEASURE.get_or_create_time_series(LABEL_VALUE_TESTING)
MEASURE_METRIC_STAGING = MEASURE.get_or_create_time_series(LABEL_VALUE_STAGING)

# record individual measures
STATISTIC = 100
MEASURE_METRIC_STAGING.record(STATISTIC)

# record multiple observed values
BATCH = MeasureBatch()
BATCH.record([(MEASURE_METRIC_TESTING, STATISTIC), (MEASURE_METRIC_STAGING, STATISTIC)])
