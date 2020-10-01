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
# type: ignore

"""
OpenTelemetry Instrumentation Metric mixin
"""
import enum
from contextlib import contextmanager
from time import time
from typing import Dict, Optional

from opentelemetry import metrics
from opentelemetry.sdk.metrics import ValueRecorder


class HTTPMetricType(enum.Enum):
    CLIENT = 0
    SERVER = 1
    # TODO: Add both


class MetricMixin:
    """Used to record metrics related to instrumentations."""

    def init_metrics(self, name: str, version: str):
        self._meter = metrics.get_meter(name, version)

    @property
    def meter(self):
        return self._meter


class MetricRecorder:
    """Base class for metric recorders of different types."""

    def __init__(self, meter: Optional[metrics.Meter] = None):
        self._meter = meter


class HTTPMetricRecorder(MetricRecorder):
    """Metric recorder for http instrumentations. Tracks duration."""

    def __init__(
        self, meter: Optional[metrics.Meter], http_type: HTTPMetricType,
    ):
        super().__init__(meter)
        self._http_type = http_type
        if self._meter:
            self._duration = self._meter.create_metric(
                name="{}.{}.duration".format(
                    "http", self._http_type.name.lower()
                ),
                description="measures the duration of the {} HTTP request".format(
                    "inbound"
                    if self._http_type is HTTPMetricType.SERVER
                    else "outbound"
                ),
                unit="ms",
                value_type=float,
                metric_type=ValueRecorder,
            )

    # Conventions for recording duration can be found at:
    # https://github.com/open-telemetry/opentelemetry-specification/blob/master/specification/metrics/semantic_conventions/http-metrics.md
    @contextmanager
    def record_duration(self, labels: Dict[str, str]):
        start_time = time()
        try:
            yield start_time
        finally:
            if self._meter:
                elapsed_time = (time() - start_time) * 1000
                self._duration.record(elapsed_time, labels)
