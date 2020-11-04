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


class HTTPMetricType(enum.Enum):
    CLIENT = 0
    SERVER = 1
    BOTH = 2


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
        self._client_duration = None
        self._server_duration = None
        if self._meter is not None:
            if http_type in (HTTPMetricType.CLIENT, HTTPMetricType.BOTH):
                self._client_duration = self._meter.create_valuerecorder(
                    name="{}.{}.duration".format("http", "client"),
                    description="measures the duration of the outbound HTTP request",
                    unit="ms",
                    value_type=float,
                )
            if http_type is not HTTPMetricType.CLIENT:
                self._server_duration = self._meter.create_valuerecorder(
                    name="{}.{}.duration".format("http", "server"),
                    description="measures the duration of the inbound HTTP request",
                    unit="ms",
                    value_type=float,
                )

    # Conventions for recording duration can be found at:
    # https://github.com/open-telemetry/opentelemetry-specification/blob/master/specification/metrics/semantic_conventions/http-metrics.md
    @contextmanager
    def record_client_duration(self, labels: Dict[str, str]):
        start_time = time()
        try:
            yield start_time
        finally:
            self.record_client_duration_range(start_time, time(), labels)

    def record_client_duration_range(
        self, start_time, end_time, labels: Dict[str, str]
    ):
        if self._client_duration is not None:
            elapsed_time = (end_time - start_time) * 1000
            self._client_duration.record(elapsed_time, labels)

    @contextmanager
    def record_server_duration(self, labels: Dict[str, str]):
        start_time = time()
        try:
            yield start_time
        finally:
            self.record_server_duration_range(start_time, time(), labels)

    def record_server_duration_range(
        self, start_time, end_time, labels: Dict[str, str]
    ):
        if self._server_duration is not None:
            elapsed_time = (end_time - start_time) * 1000
            self._server_duration.record(elapsed_time, labels)
