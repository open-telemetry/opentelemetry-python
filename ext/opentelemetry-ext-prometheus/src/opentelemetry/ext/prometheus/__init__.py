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

import collections
import logging
import re
from typing import Sequence

from prometheus_client.core import (
    REGISTRY,
    CounterMetricFamily,
    GaugeMetricFamily,
    UnknownMetricFamily,
)

from opentelemetry.metrics import Counter, Gauge, Measure
from opentelemetry.sdk.metrics.export import (
    MetricRecord,
    MetricsExporter,
    MetricsExportResult,
)

logger = logging.getLogger(__name__)


class PrometheusMetricsExporter(MetricsExporter):
    """Prometheus metric exporter for OpenTelemetry.

    Args:
        prefix: single-word application prefix relevant to the domain
        the metric belongs to.
    """

    def __init__(self, prefix: str = ""):
        self._collector = CustomCollector(prefix)
        REGISTRY.register(self._collector)

    def export(
        self, metric_records: Sequence[MetricRecord]
    ) -> MetricsExportResult:
        self._collector.add_metrics_data(metric_records)
        return MetricsExportResult.SUCCESS

    def shutdown(self) -> None:
        REGISTRY.unregister(self._collector)


class CustomCollector:
    """ CustomCollector represents the Prometheus Collector object
        https://github.com/prometheus/client_python#custom-collectors
    """

    def __init__(self, prefix: str = ""):
        self._prefix = prefix
        self._metrics_to_export = collections.deque()
        self._non_letters_nor_digits_re = re.compile(
            r"[^\w]", re.UNICODE | re.IGNORECASE
        )

    def add_metrics_data(self, metric_records: Sequence[MetricRecord]):
        self._metrics_to_export.append(metric_records)

    def collect(self):
        """Collect fetches the metrics from OpenTelemetry
        and delivers them as Prometheus Metrics.
        Collect is invoked every time a prometheus.Gatherer is run
        for example when the HTTP endpoint is invoked by Prometheus.
        """

        while self._metrics_to_export:
            for metric_record in self._metrics_to_export.popleft():
                prometheus_metric = self._translate_to_prometheus(
                    metric_record
                )
                if prometheus_metric is not None:
                    yield prometheus_metric

    def _translate_to_prometheus(self, metric_record: MetricRecord):
        prometheus_metric = None
        label_values = []
        label_keys = []
        for label_tuple in metric_record.label_set.labels:
            label_keys.append(self._sanitize(label_tuple[0]))
            label_values.append(label_tuple[1])

        metric_name = ""
        if self._prefix != "":
            metric_name = self._prefix + "_"
        metric_name += self._sanitize(metric_record.metric.name)

        if isinstance(metric_record.metric, Counter):
            prometheus_metric = CounterMetricFamily(
                name=metric_name,
                documentation=metric_record.metric.description,
                labels=label_keys,
            )
            prometheus_metric.add_metric(
                labels=label_values, value=metric_record.aggregator.checkpoint
            )

        elif isinstance(metric_record.metric, Gauge):
            prometheus_metric = GaugeMetricFamily(
                name=metric_name,
                documentation=metric_record.metric.description,
                labels=label_keys,
            )
            prometheus_metric.add_metric(
                labels=label_values, value=metric_record.aggregator.checkpoint
            )

        # TODO: Add support for histograms when supported in OT
        elif isinstance(metric_record.metric, Measure):
            prometheus_metric = UnknownMetricFamily(
                name=metric_name,
                documentation=metric_record.metric.description,
                labels=label_keys,
            )
            prometheus_metric.add_metric(
                labels=label_values, value=metric_record.aggregator.checkpoint
            )

        else:
            logger.warning(
                "Unsupported metric type. %s", type(metric_record.metric)
            )
        return prometheus_metric

    def _sanitize(self, key):
        """ sanitize the given metric name or label according to Prometheus rule.
        Replace all characters other than [A-Za-z0-9_] with '_'.
        """
        return self._non_letters_nor_digits_re.sub("_", key)
