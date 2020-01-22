# Copyright 2020, OpenTelemetry Authors
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

"""Prometheus Metrics Exporter for OpenTelemetry."""

import logging
import re
from typing import Sequence

from prometheus_client import start_http_server
from prometheus_client.core import (
    REGISTRY,
    CollectorRegistry,
    CounterMetricFamily,
    GaugeMetricFamily,
    UnknownMetricFamily,
)

from opentelemetry.sdk.metrics.export import (
    MetricsExporter,
    MetricsExportResult,
    MetricRecord,
)
from opentelemetry.metrics import Metric, Counter, Gauge, Measure

logger = logging.getLogger(__name__)

DEFAULT_PORT = 8000


class PrometheusMetricsExporter(MetricsExporter):
    """Prometheus metric exporter for OpenTelemetry.

    Args:
        port: The Prometheus port to be used.
        address: The Prometheus address to be used.
    """

    def __init__(
        self,
        port: int = DEFAULT_PORT,
        address: str = ""
    ):
        self._port = port
        self._address = address
        self._collector = CustomCollector()

        start_http_server(port=self._port, addr=str(self._address))
        REGISTRY.register(self._collector)

    def export(
        self, metric_records: Sequence[MetricRecord]
    ) -> MetricsExportResult:
        self._collector.add_metrics_data(metric_records)
        return MetricsExportResult.SUCCESS

    def shutdown(self) -> None:
        REGISTRY.unregister(self._collector)


class CustomCollector(object):
    """ CustomCollector represents the Prometheus Collector object
        https://github.com/prometheus/client_python#custom-collectors
    """

    def __init__(self):
        self._metrics_to_export = []

    def add_metrics_data(self, metric_records: Sequence[MetricRecord]):
        self._metrics_to_export.append(metric_records)

    def collect(self):
        """Collect fetches the metrics from OpenTelemetry
        and delivers them as Prometheus Metrics.
        Collect is invoked every time a prometheus.Gatherer is run
        for example when the HTTP endpoint is invoked by Prometheus.
        """

        for metric_batch in list(self._metrics_to_export):
            for metric_record in metric_batch:
                prometheus_metric = self._translate_to_prometheus(
                    metric_record
                )
                if prometheus_metric:
                    yield prometheus_metric
            self._metrics_to_export.remove(metric_batch)

    def _translate_to_prometheus(self, metric_record: MetricRecord):
        label_values = metric_record.label_set.labels.values()
        prometheus_metric = None

        metric_name = sanitize(metric_record.metric.name)

        if isinstance(metric_record.metric, Counter):
            prometheus_metric = CounterMetricFamily(
                name=metric_name,
                documentation=metric_record.metric.description,
                labels=metric_record.metric.label_keys,
            )
            prometheus_metric.add_metric(
                labels=label_values, value=metric_record.aggregator.check_point
            )

        elif isinstance(metric_record.metric, Gauge):
            prometheus_metric = GaugeMetricFamily(
                name=metric_name,
                documentation=metric_record.metric.description,
            )
            prometheus_metric.add_metric(
                labels=label_values, value=metric_record.aggregator.check_point
            )

        elif isinstance(metric_record.metric, Measure):
            prometheus_metric = UnknownMetricFamily(
                name=metric_name,
                documentation=metric_record.metric.description,
            )
            prometheus_metric.add_metric(
                labels=label_values, value=metric_record.aggregator.check_point
            )

        else:
            logger.warning(
                "Unsupported metric type. %s", type(metric_record.metric)
            )
        return prometheus_metric


_NON_LETTERS_NOR_DIGITS_RE = re.compile(r"[^\w]", re.UNICODE | re.IGNORECASE)


def sanitize(key):
    """ sanitize the given metric name or label according to Prometheus rule.
    Replace all characters other than [A-Za-z0-9_] with '_'.
    """
    return _NON_LETTERS_NOR_DIGITS_RE.sub("_", key)
