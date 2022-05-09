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

from collections import deque
from itertools import chain
from json import dumps
from logging import getLogger
from re import IGNORECASE, UNICODE, compile
from typing import Dict, Iterable, Sequence, Tuple, Union

from prometheus_client.core import (
    REGISTRY,
    CounterMetricFamily,
    GaugeMetricFamily,
    HistogramMetricFamily,
)
from prometheus_client.core import Metric as PrometheusMetric

from opentelemetry.sdk._metrics.export import (
    Gauge,
    Histogram,
    Metric,
    MetricReader,
    Sum,
)

_logger = getLogger(__name__)


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
        REGISTRY.register(self._collector)
        self._collector._callback = self.collect

    def _receive_metrics(
        self,
        metrics: Iterable[Metric],
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> None:
        if metrics is None:
            return
        self._collector.add_metrics_data(metrics)

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        REGISTRY.unregister(self._collector)


class _CustomCollector:
    """_CustomCollector represents the Prometheus Collector object

    See more:
    https://github.com/prometheus/client_python#custom-collectors
    """

    def __init__(self, prefix: str = ""):
        self._prefix = prefix
        self._callback = None
        self._metrics_to_export = deque()
        self._non_letters_digits_underscore_re = compile(
            r"[^\w]", UNICODE | IGNORECASE
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

        metric_family_id_metric_family = {}

        while self._metrics_to_export:
            for export_record in self._metrics_to_export.popleft():
                self._translate_to_prometheus(
                    export_record, metric_family_id_metric_family
                )

            if metric_family_id_metric_family:
                for metric_family in metric_family_id_metric_family.values():
                    yield metric_family

    def _translate_to_prometheus(
        self,
        metric: Metric,
        metric_family_id_metric_family: Dict[str, PrometheusMetric],
    ):
        label_values = []
        label_keys = []
        for key, value in metric.attributes.items():
            label_keys.append(self._sanitize(key))
            label_values.append(self._check_value(value))

        metric_name = ""
        if self._prefix != "":
            metric_name = self._prefix + "_"
        metric_name += self._sanitize(metric.name)

        description = metric.description or ""

        metric_family_id = "|".join(
            [metric_name, description, "%".join(label_keys), metric.unit]
        )

        if isinstance(metric.point, Sum):

            metric_family_id = "|".join(
                [metric_family_id, CounterMetricFamily.__name__]
            )

            if metric_family_id not in metric_family_id_metric_family.keys():
                metric_family_id_metric_family[
                    metric_family_id
                ] = CounterMetricFamily(
                    name=metric_name,
                    documentation=description,
                    labels=label_keys,
                    unit=metric.unit,
                )
            metric_family_id_metric_family[metric_family_id].add_metric(
                labels=label_values, value=metric.point.value
            )
        elif isinstance(metric.point, Gauge):

            metric_family_id = "|".join(
                [metric_family_id, GaugeMetricFamily.__name__]
            )

            if metric_family_id not in metric_family_id_metric_family.keys():
                metric_family_id_metric_family[
                    metric_family_id
                ] = GaugeMetricFamily(
                    name=metric_name,
                    documentation=description,
                    labels=label_keys,
                    unit=metric.unit,
                )
            metric_family_id_metric_family[metric_family_id].add_metric(
                labels=label_values, value=metric.point.value
            )
        elif isinstance(metric.point, Histogram):

            metric_family_id = "|".join(
                [metric_family_id, HistogramMetricFamily.__name__]
            )

            if metric_family_id not in metric_family_id_metric_family.keys():
                metric_family_id_metric_family[
                    metric_family_id
                ] = HistogramMetricFamily(
                    name=metric_name,
                    documentation=description,
                    labels=label_keys,
                    unit=metric.unit,
                )
            metric_family_id_metric_family[metric_family_id].add_metric(
                labels=label_values,
                buckets=_convert_buckets(metric),
                sum_value=metric.point.sum,
            )
        else:
            _logger.warning("Unsupported metric type. %s", type(metric.point))

    def _sanitize(self, key: str) -> str:
        """sanitize the given metric name or label according to Prometheus rule.
        Replace all characters other than [A-Za-z0-9_] with '_'.
        """
        return self._non_letters_digits_underscore_re.sub("_", key)

    # pylint: disable=no-self-use
    def _check_value(self, value: Union[int, float, str, Sequence]) -> str:
        """Check the label value and return is appropriate representation"""
        if not isinstance(value, str):
            return dumps(value, default=str)
        return str(value)
