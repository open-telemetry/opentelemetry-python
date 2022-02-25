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

The **OpenTelemetry Prometheus Exporter** allows export of `OpenTelemetry`_ metrics to `Prometheus`_.


.. _Prometheus: https://prometheus.io/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/

.. code:: python

    from opentelemetry import metrics
    from opentelemetry.exporter.prometheus import PrometheusMetricExporter
    from opentelemetry.sdk.metrics import Meter
    from prometheus_client import start_http_server

    # Start Prometheus client
    start_http_server(port=8000, addr="localhost")

    # Meter is responsible for creating and recording metrics
    metrics.set_meter_provider(MeterProvider())
    meter = metrics.get_meter(__name__)
    # exporter to export metrics to Prometheus
    prefix = "MyAppPrefix"
    exporter = PrometheusMetricExporter(prefix)
    # Starts the collect/export pipeline for metrics
    metrics.get_meter_provider().start_pipeline(meter, exporter, 5)

    counter = meter.create_counter(
        "requests",
        "number of requests",
        "requests",
        int,
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
from typing import Optional, Sequence, Tuple

from prometheus_client import core

from opentelemetry.sdk._metrics.export import (
    MetricExporter,
    MetricExportResult,
)
from opentelemetry.sdk._metrics.point import Gauge, Histogram, Metric, Sum

logger = logging.getLogger(__name__)


class PrometheusMetricExporter(MetricExporter):
    """Prometheus metric exporter for OpenTelemetry.

    Args:
        prefix: single-word application prefix relevant to the domain
            the metric belongs to.
    """

    def __init__(self, prefix: str = ""):
        self._collector = CustomCollector(prefix)
        core.REGISTRY.register(self._collector)

    def export(self, export_records: Sequence[Metric]) -> MetricExportResult:
        self._collector.add_metrics_data(export_records)
        return MetricExportResult.SUCCESS

    def shutdown(self) -> None:
        core.REGISTRY.unregister(self._collector)


class CustomCollector:
    """CustomCollector represents the Prometheus Collector object
    https://github.com/prometheus/client_python#custom-collectors
    """

    def __init__(self, prefix: str = ""):
        self._prefix = prefix
        self._metrics_to_export = collections.deque()
        self._non_letters_nor_digits_re = re.compile(
            r"[^\w]", re.UNICODE | re.IGNORECASE
        )

    def add_metrics_data(self, export_records: Sequence[Metric]) -> None:
        self._metrics_to_export.append(export_records)

    def collect(self) -> None:
        """Collect fetches the metrics from OpenTelemetry
        and delivers them as Prometheus Metrics.
        Collect is invoked every time a prometheus.Gatherer is run
        for example when the HTTP endpoint is invoked by Prometheus.
        """

        while self._metrics_to_export:
            for export_record in self._metrics_to_export.popleft():
                prometheus_metric = self._translate_to_prometheus(
                    export_record
                )
                if prometheus_metric is not None:
                    yield prometheus_metric

    def _convert_buckets(self, metric: Metric) -> Sequence[Tuple[str, int]]:
        buckets = []
        total_count = 0
        for i in range(0, len(metric.point.bucket_counts)):
            total_count += metric.point.bucket_counts[i]
            buckets.append(
                (
                    f"{metric.point.explicit_bounds[i]}",
                    total_count,
                )
            )
        return buckets

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
            buckets = self._convert_buckets(metric)
            prometheus_metric.add_metric(
                labels=label_values, buckets=buckets, sum_value=value
            )
        # TODO: add support for Summary once implemented
        # elif isinstance(export_record.point, Summary):
        else:
            logger.warning("Unsupported metric type. %s", type(metric.point))
        return prometheus_metric

    def _sanitize(self, key: str) -> str:
        """sanitize the given metric name or label according to Prometheus rule.
        Replace all characters other than [A-Za-z0-9_] with '_'.
        """
        return self._non_letters_nor_digits_re.sub("_", key)
