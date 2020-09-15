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
from contextlib import contextmanager
from time import time

from opentelemetry import metrics
from opentelemetry.sdk.metrics import PushController, ValueRecorder
from opentelemetry.trace import SpanKind


class MetricMixin:
    """Used to record metrics related to instrumentations."""

    def init_metrics(self, name, version, exporter=None, interval=None):
        self._meter = metrics.get_meter(name, version)
        if exporter and interval:
            self._controller = PushController(
                meter=self._meter, exporter=exporter, interval=interval
            )

    @property
    def meter(self):
        return self._meter


class MetricRecorder:
    """Base class for metric recorders of different types."""

    def __init__(self, meter):
        self._meter = meter


class HTTPMetricRecorder(MetricRecorder):
    """Metric recorder for http instrumentations. Tracks duration."""

    def __init__(self, meter, kind: SpanKind):
        super().__init__(meter)
        self.kind = kind
        if self._meter:
            self._duration = self._meter.create_metric(
                name="{}.{}.duration".format("http", self.kind.name.lower()),
                description="measures the duration of the {} HTTP request".format(
                    "inbound" if self.kind is SpanKind.SERVER else "outbound"
                ),
                unit="ms",
                value_type=float,
                metric_type=ValueRecorder,
            )

    @contextmanager
    def record_duration(self, labels):
        start_time = time()
        try:
            yield start_time
        finally:
            if self._meter:
                elapsed_time = (time() - start_time) * 1000
                self._duration.record(elapsed_time, labels)
