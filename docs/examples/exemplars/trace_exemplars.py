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
This example shows how to generate trace exemplars for a histogram, and how to export them to Google Cloud Monitoring.
"""

import random
import time

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider, ValueRecorder
from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter
from opentelemetry.sdk.metrics.export.aggregate import HistogramAggregator
from opentelemetry.sdk.metrics.view import View, ViewConfig

# Set up OpenTelemetry metrics
metrics.set_meter_provider(MeterProvider(stateful=False))
meter = metrics.get_meter(__name__)

# Use the Google Cloud Monitoring Metrics Exporter since its the only one that currently supports exemplars
metrics.get_meter_provider().start_pipeline(
    meter, ConsoleMetricsExporter(), 10
)

# Create our duration metric
request_duration = meter.create_metric(
    name="request_duration",
    description="duration (ms) of incoming requests",
    unit="ms",
    value_type=int,
    metric_type=ValueRecorder,
)

# Add a Histogram view to our duration metric, and make it generate 1 exemplars per bucket
duration_view = View(
    request_duration,
    # Latency in buckets:
    # [>=0ms, >=25ms, >=50ms, >=75ms, >=100ms, >=200ms, >=400ms, >=600ms, >=800ms, >=1s, >=2s, >=4s, >=6s]
    # We want to generate 1 exemplar per bucket, where each exemplar has a linked trace that was recorded.
    # So we need to set num_exemplars to 1 and not specify statistical_exemplars (defaults to false)
    HistogramAggregator,
    aggregator_config={
        "bounds": [
            0,
            25,
            50,
            75,
            100,
            200,
            400,
            600,
            800,
            1000,
            2000,
            4000,
            6000,
        ],
        "num_exemplars": 1,
    },
    label_keys=["environment"],
    view_config=ViewConfig.LABEL_KEYS,
)

meter.register_view(duration_view)

for i in range(100):
    # Generate some random data for the histogram with a dropped label "customer_id"
    request_duration.record(
        random.randint(1, 8000),
        {"environment": "staging", "customer_id": random.randint(1, 100)},
    )
    time.sleep(1)
