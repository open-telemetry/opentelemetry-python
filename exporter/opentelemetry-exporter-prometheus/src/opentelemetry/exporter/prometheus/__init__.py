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

"""
This library allows export of metrics data to `Prometheus <https://prometheus.io/>`_.

Usage
-----

The **OpenTelemetry Prometheus Exporter** allows export of `OpenTelemetry`_
metrics to `Prometheus`_.


.. _Prometheus: https://prometheus.io/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/

.. code:: python

    from prometheus_client import start_http_server

    from opentelemetry._metrics import get_meter_provider, set_meter_provider
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from opentelemetry.sdk._metrics import MeterProvider

    # Start Prometheus client
    start_http_server(port=8000, addr="localhost")

    # Exporter to export metrics to Prometheus
    prefix = "MyAppPrefix"
    reader = PrometheusMetricReader(prefix)

    # Meter is responsible for creating and recording metrics
    set_meter_provider(MeterProvider(metric_readers=[reader]))
    meter = get_meter_provider().get_meter("myapp", "0.1.2")

    counter = meter.create_counter(
        "requests",
        "requests",
        "number of requests",
    )

    # Labels are used to identify key-values that are associated with a specific
    # metric that you want to record. These are useful for pre-aggregation and can
    # be used to store custom dimensions pertaining to a metric
    labels = {"environment": "staging"}

    counter.add(25, labels)
    input("Press any key to exit...")

API
---
"""

import collections
import logging
import re
from itertools import chain
from typing import Iterable, Optional, Sequence, Tuple

from prometheus_client import core

from opentelemetry.sdk._metrics.export import MetricReader
from opentelemetry.sdk._metrics.point import Gauge, Histogram, Metric, Sum

_logger = logging.getLogger(__name__)


def _convert_buckets(metric: Metric) -> Sequence[Tuple[str, int]]:
    buckets = []
    total_count = 0
    for upper_bound, count in zip(
        chain(metric.point.explicit_bounds, ["+Inf"]),
        metric.point.bucket_counts,
    ):
        total_count += count
        buckets.append((f"{upper_bound}", total_count))

    return buckets


class PrometheusMetricReader(MetricReader):
    """Prometheus metric exporter for OpenTelemetry.

    Args:
        prefix: single-word application prefix relevant to the domain
            the metric belongs to.
    """

    def __init__(self, prefix: str = "") -> None:
        super().__init__()
        self._collector = _CustomCollector(prefix)
        core.REGISTRY.register(self._collector)
        self._collector._callback = self.collect

    def _receive_metrics(self, metrics: Iterable[Metric]) -> None:
        if metrics is None:
            return
        self._collector.add_metrics_data(metrics)

    def shutdown(self) -> bool:
        core.REGISTRY.unregister(self._collector)
        return True


class _CustomCollector:
    """_CustomCollector represents the Prometheus Collector object

    See more:
    https://github.com/prometheus/client_python#custom-collectors
    """

    def __init__(self, prefix: str = ""):
        self._prefix = prefix
        self._callback = None
        self._metrics_to_export = collections.deque()
        self._non_letters_digits_underscore_re = re.compile(
            r"[^\w]", re.UNICODE | re.IGNORECASE
        )

    def add_metrics_data(self, export_records: Sequence[Metric]) -> None:
        """Add metrics to Prometheus data"""
        self._metrics_to_export.append(export_records)

    def collect(self) -> None:
        """Collect fetches the metrics from OpenTelemetry
        and delivers them as Prometheus Metrics.
        Collect is invoked every time a ``prometheus.Gatherer`` is run
        for example when the HTTP endpoint is invoked by Prometheus.
        """
        if self._callback is not None:
            self._callback()

        while self._metrics_to_export:
            for export_record in self._metrics_to_export.popleft():
                prometheus_metric = self._translate_to_prometheus(
                    export_record
                )
                if prometheus_metric is not None:
                    yield prometheus_metric

    def _translate_to_prometheus(
        self, metric: Metric
    ) -> Optional[core.Metric]:
        prometheus_metric = None
        label_values = []
        label_keys = []
        for key, value in metric.attributes.items():
            label_keys.append(self._sanitize(key))
            label_values.append(str(value))

        metric_name = ""
        if self._prefix != "":
            metric_name = self._prefix + "_"
        metric_name += self._sanitize(metric.name)

        description = metric.description or ""
        if isinstance(metric.point, Sum):
            prometheus_metric = core.CounterMetricFamily(
                name=metric_name,
                documentation=description,
                labels=label_keys,
                unit=metric.unit,
            )
            prometheus_metric.add_metric(
                labels=label_values, value=metric.point.value
            )
        elif isinstance(metric.point, Gauge):
            prometheus_metric = core.GaugeMetricFamily(
                name=metric_name,
                documentation=description,
                labels=label_keys,
                unit=metric.unit,
            )
            prometheus_metric.add_metric(
                labels=label_values, value=metric.point.value
            )
        elif isinstance(metric.point, Histogram):
            value = metric.point.sum
            prometheus_metric = core.HistogramMetricFamily(
                name=metric_name,
                documentation=description,
                labels=label_keys,
                unit=metric.unit,
            )
            buckets = _convert_buckets(metric)
            prometheus_metric.add_metric(
                labels=label_values, buckets=buckets, sum_value=value
            )
        else:
            _logger.warning("Unsupported metric type. %s", type(metric.point))
        return prometheus_metric

    def _sanitize(self, key: str) -> str:
        """sanitize the given metric name or label according to Prometheus rule.
        Replace all characters other than [A-Za-z0-9_] with '_'.
        """
        return self._non_letters_digits_underscore_re.sub("_", key)
