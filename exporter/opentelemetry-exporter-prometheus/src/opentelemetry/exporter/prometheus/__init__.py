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

    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from opentelemetry.metrics import get_meter_provider, set_meter_provider
    from opentelemetry.sdk.metrics import MeterProvider

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
from typing import Dict, Sequence, Tuple, Union

from prometheus_client.core import (
    REGISTRY,
    CounterMetricFamily,
    GaugeMetricFamily,
    HistogramMetricFamily,
)
from prometheus_client.core import Metric as PrometheusMetric

from opentelemetry.sdk.metrics import Counter
from opentelemetry.sdk.metrics import Histogram as HistogramInstrument
from opentelemetry.sdk.metrics import (
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    Gauge,
    Histogram,
    HistogramDataPoint,
    MetricReader,
    MetricsData,
    Sum,
)

_logger = getLogger(__name__)


def _convert_buckets(
    bucket_counts: Sequence[int], explicit_bounds: Sequence[float]
) -> Sequence[Tuple[str, int]]:
    buckets = []
    total_count = 0
    for upper_bound, count in zip(
        chain(explicit_bounds, ["+Inf"]),
        bucket_counts,
    ):
        total_count += count
        buckets.append((f"{upper_bound}", total_count))

    return buckets


class PrometheusMetricReader(MetricReader):
    """Prometheus metric exporter for OpenTelemetry."""

    def __init__(self) -> None:

        super().__init__(
            preferred_temporality={
                Counter: AggregationTemporality.CUMULATIVE,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                HistogramInstrument: AggregationTemporality.CUMULATIVE,
                ObservableCounter: AggregationTemporality.CUMULATIVE,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }
        )
        self._collector = _CustomCollector()
        REGISTRY.register(self._collector)
        self._collector._callback = self.collect

    def _receive_metrics(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> None:
        if metrics_data is None:
            return
        self._collector.add_metrics_data(metrics_data)

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        REGISTRY.unregister(self._collector)


class _CustomCollector:
    """_CustomCollector represents the Prometheus Collector object

    See more:
    https://github.com/prometheus/client_python#custom-collectors
    """

    def __init__(self):
        self._callback = None
        self._metrics_datas = deque()
        self._non_letters_digits_underscore_re = compile(
            r"[^\w]", UNICODE | IGNORECASE
        )

    def add_metrics_data(self, metrics_data: MetricsData) -> None:
        """Add metrics to Prometheus data"""
        self._metrics_datas.append(metrics_data)

    def collect(self) -> None:
        """Collect fetches the metrics from OpenTelemetry
        and delivers them as Prometheus Metrics.
        Collect is invoked every time a ``prometheus.Gatherer`` is run
        for example when the HTTP endpoint is invoked by Prometheus.
        """
        if self._callback is not None:
            self._callback()

        metric_family_id_metric_family = {}

        while self._metrics_datas:
            self._translate_to_prometheus(
                self._metrics_datas.popleft(), metric_family_id_metric_family
            )

            if metric_family_id_metric_family:
                for metric_family in metric_family_id_metric_family.values():
                    yield metric_family

    # pylint: disable=too-many-locals,too-many-branches
    def _translate_to_prometheus(
        self,
        metrics_data: MetricsData,
        metric_family_id_metric_family: Dict[str, PrometheusMetric],
    ):
        metrics = []

        for resource_metrics in metrics_data.resource_metrics:
            for scope_metrics in resource_metrics.scope_metrics:
                for metric in scope_metrics.metrics:
                    metrics.append(metric)

        for metric in metrics:
            label_valuess = []
            values = []

            pre_metric_family_ids = []

            metric_name = ""
            metric_name += self._sanitize(metric.name)

            metric_description = metric.description or ""

            for number_data_point in metric.data.data_points:
                label_keys = []
                label_values = []

                for key, value in number_data_point.attributes.items():
                    label_keys.append(self._sanitize(key))
                    label_values.append(self._check_value(value))

                pre_metric_family_ids.append(
                    "|".join(
                        [
                            metric_name,
                            metric_description,
                            "%".join(label_keys),
                            metric.unit,
                        ]
                    )
                )

                label_valuess.append(label_values)
                if isinstance(number_data_point, HistogramDataPoint):
                    values.append(
                        {
                            "bucket_counts": number_data_point.bucket_counts,
                            "explicit_bounds": (
                                number_data_point.explicit_bounds
                            ),
                            "sum": number_data_point.sum,
                        }
                    )
                else:
                    values.append(number_data_point.value)

            for pre_metric_family_id, label_values, value in zip(
                pre_metric_family_ids, label_valuess, values
            ):
                if isinstance(metric.data, Sum):

                    metric_family_id = "|".join(
                        [pre_metric_family_id, CounterMetricFamily.__name__]
                    )

                    if metric_family_id not in metric_family_id_metric_family:
                        metric_family_id_metric_family[
                            metric_family_id
                        ] = CounterMetricFamily(
                            name=metric_name,
                            documentation=metric_description,
                            labels=label_keys,
                            unit=metric.unit,
                        )
                    metric_family_id_metric_family[
                        metric_family_id
                    ].add_metric(labels=label_values, value=value)
                elif isinstance(metric.data, Gauge):

                    metric_family_id = "|".join(
                        [pre_metric_family_id, GaugeMetricFamily.__name__]
                    )

                    if (
                        metric_family_id
                        not in metric_family_id_metric_family.keys()
                    ):
                        metric_family_id_metric_family[
                            metric_family_id
                        ] = GaugeMetricFamily(
                            name=metric_name,
                            documentation=metric_description,
                            labels=label_keys,
                            unit=metric.unit,
                        )
                    metric_family_id_metric_family[
                        metric_family_id
                    ].add_metric(labels=label_values, value=value)
                elif isinstance(metric.data, Histogram):

                    metric_family_id = "|".join(
                        [pre_metric_family_id, HistogramMetricFamily.__name__]
                    )

                    if (
                        metric_family_id
                        not in metric_family_id_metric_family.keys()
                    ):
                        metric_family_id_metric_family[
                            metric_family_id
                        ] = HistogramMetricFamily(
                            name=metric_name,
                            documentation=metric_description,
                            labels=label_keys,
                            unit=metric.unit,
                        )
                    metric_family_id_metric_family[
                        metric_family_id
                    ].add_metric(
                        labels=label_values,
                        buckets=_convert_buckets(
                            value["bucket_counts"], value["explicit_bounds"]
                        ),
                        sum_value=value["sum"],
                    )
                else:
                    _logger.warning(
                        "Unsupported metric data. %s", type(metric.data)
                    )

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
