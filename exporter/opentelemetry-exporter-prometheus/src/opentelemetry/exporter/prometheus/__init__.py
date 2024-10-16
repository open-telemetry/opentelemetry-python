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
from os import environ
from typing import Deque, Dict, Iterable, Optional, Sequence, Tuple, Union

from prometheus_client import start_http_server
from prometheus_client.core import (
    REGISTRY,
    CounterMetricFamily,
    GaugeMetricFamily,
    HistogramMetricFamily,
    InfoMetricFamily,
)
from prometheus_client.core import Metric as PrometheusMetric
from prometheus_client.samples import Exemplar as PrometheusExemplar

from opentelemetry.exporter.prometheus._mapping import (
    map_unit,
    sanitize_attribute,
    sanitize_full_name,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_PROMETHEUS_HOST,
    OTEL_EXPORTER_PROMETHEUS_PORT,
    OTEL_PYTHON_EXPERIMENTAL_DISABLE_PROMETHEUS_UNIT_NORMALIZATION,
)
from opentelemetry.sdk.metrics import (
    Counter,
    Exemplar,
    Histogram as HistogramInstrument,
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
from opentelemetry.trace import format_span_id, format_trace_id
from opentelemetry.util.types import Attributes

_logger = getLogger(__name__)

_TARGET_INFO_NAME = "target"
_TARGET_INFO_DESCRIPTION = "Target metadata"


def _convert_buckets(
    bucket_counts: Sequence[int],
    explicit_bounds: Sequence[float],
    exemplars: Optional[Sequence[PrometheusExemplar]] = None,
) -> Sequence[Tuple[str, int, Optional[Exemplar]]]:
    buckets = []
    total_count = 0
    previous_bound = float("-inf")

    exemplars = list(reversed(exemplars or []))
    exemplar = exemplars.pop() if exemplars else None

    for upper_bound, count in zip(
        chain(explicit_bounds, ["+Inf"]),
        bucket_counts,
    ):
        total_count += count
        current_exemplar = None
        upper_bound_f = float(upper_bound)
        while exemplar and previous_bound <= exemplar.value < upper_bound_f:
            if current_exemplar is None:
                # Assign the exemplar to the current bucket if it's the first valid one found
                current_exemplar = exemplar
            exemplar = exemplars.pop() if exemplars else None
        previous_bound = upper_bound_f

        buckets.append((f"{upper_bound}", total_count, current_exemplar))

    return buckets


class PrometheusMetricReader(MetricReader):
    """Prometheus metric exporter for OpenTelemetry."""

    def __init__(self, disable_target_info: bool = False) -> None:
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
        self._collector = _CustomCollector(disable_target_info)
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

    def __init__(self, disable_target_info: bool = False):
        self._callback = None
        self._metrics_datas: Deque[MetricsData] = deque()
        self._disable_target_info = disable_target_info
        self._target_info = None

    def add_metrics_data(self, metrics_data: MetricsData) -> None:
        """Add metrics to Prometheus data"""
        self._metrics_datas.append(metrics_data)

    def collect(self) -> Iterable[PrometheusMetric]:
        """Collect fetches the metrics from OpenTelemetry
        and delivers them as Prometheus Metrics.
        Collect is invoked every time a ``prometheus.Gatherer`` is run
        for example when the HTTP endpoint is invoked by Prometheus.
        """
        if self._callback is not None:
            self._callback()

        metric_family_id_metric_family = {}

        if len(self._metrics_datas):
            if not self._disable_target_info:
                if self._target_info is None:
                    attributes: Attributes = {}
                    for res in self._metrics_datas[0].resource_metrics:
                        attributes = {**attributes, **res.resource.attributes}

                    self._target_info = self._create_info_metric(
                        _TARGET_INFO_NAME, _TARGET_INFO_DESCRIPTION, attributes
                    )
                metric_family_id_metric_family[_TARGET_INFO_NAME] = (
                    self._target_info
                )

        while self._metrics_datas:
            self._translate_to_prometheus(
                self._metrics_datas.popleft(), metric_family_id_metric_family
            )

            if metric_family_id_metric_family:
                yield from metric_family_id_metric_family.values()

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

            metric_name = sanitize_full_name(metric.name)

            metric_description = metric.description or ""

            # TODO(#3929): remove this opt-out option
            disable_unit_normalization = (
                environ.get(
                    OTEL_PYTHON_EXPERIMENTAL_DISABLE_PROMETHEUS_UNIT_NORMALIZATION,
                    "false",
                ).lower()
                == "true"
            )
            if disable_unit_normalization:
                metric_unit = metric.unit
            else:
                metric_unit = map_unit(metric.unit)

            for number_data_point in metric.data.data_points:
                label_keys = []
                label_values = []
                exemplars = [
                    self._convert_exemplar(ex)
                    for ex in number_data_point.exemplars
                ]

                for key, value in sorted(number_data_point.attributes.items()):
                    label_keys.append(sanitize_attribute(key))
                    label_values.append(self._check_value(value))

                pre_metric_family_ids.append(
                    "|".join(
                        [
                            metric_name,
                            metric_description,
                            "%".join(label_keys),
                            metric_unit,
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
                            "exemplars": exemplars,
                        }
                    )
                else:
                    values.append(number_data_point.value)

            for pre_metric_family_id, label_values, value in zip(
                pre_metric_family_ids, label_valuess, values
            ):
                is_non_monotonic_sum = (
                    isinstance(metric.data, Sum)
                    and metric.data.is_monotonic is False
                )
                is_cumulative = (
                    isinstance(metric.data, Sum)
                    and metric.data.aggregation_temporality
                    == AggregationTemporality.CUMULATIVE
                )

                # The prometheus compatibility spec for sums says: If the aggregation temporality is cumulative and the sum is non-monotonic, it MUST be converted to a Prometheus Gauge.
                should_convert_sum_to_gauge = (
                    is_non_monotonic_sum and is_cumulative
                )

                if (
                    isinstance(metric.data, Sum)
                    and not should_convert_sum_to_gauge
                ):
                    metric_family_id = "|".join(
                        [pre_metric_family_id, CounterMetricFamily.__name__]
                    )

                    if metric_family_id not in metric_family_id_metric_family:
                        metric_family_id_metric_family[metric_family_id] = (
                            CounterMetricFamily(
                                name=metric_name,
                                documentation=metric_description,
                                labels=label_keys,
                                unit=metric_unit,
                            )
                        )
                    metric_family_id_metric_family[
                        metric_family_id
                    ].add_metric(labels=label_values, value=value)
                elif (
                    isinstance(metric.data, Gauge)
                    or should_convert_sum_to_gauge
                ):
                    metric_family_id = "|".join(
                        [pre_metric_family_id, GaugeMetricFamily.__name__]
                    )

                    if (
                        metric_family_id
                        not in metric_family_id_metric_family.keys()
                    ):
                        metric_family_id_metric_family[metric_family_id] = (
                            GaugeMetricFamily(
                                name=metric_name,
                                documentation=metric_description,
                                labels=label_keys,
                                unit=metric_unit,
                            )
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
                        metric_family_id_metric_family[metric_family_id] = (
                            HistogramMetricFamily(
                                name=metric_name,
                                documentation=metric_description,
                                labels=label_keys,
                                unit=metric_unit,
                            )
                        )
                    metric_family_id_metric_family[
                        metric_family_id
                    ].add_metric(
                        labels=label_values,
                        buckets=_convert_buckets(
                            value["bucket_counts"],
                            value["explicit_bounds"],
                            value["exemplars"],
                        ),
                        sum_value=value["sum"],
                    )
                else:
                    _logger.warning(
                        "Unsupported metric data. %s", type(metric.data)
                    )

    # pylint: disable=no-self-use
    def _check_value(self, value: Union[int, float, str, Sequence]) -> str:
        """Check the label value and return is appropriate representation"""
        if not isinstance(value, str):
            return dumps(value, default=str)
        return str(value)

    def _create_info_metric(
        self, name: str, description: str, attributes: Dict[str, str]
    ) -> InfoMetricFamily:
        """Create an Info Metric Family with list of attributes"""
        # sanitize the attribute names according to Prometheus rule
        attributes = {
            sanitize_attribute(key): self._check_value(value)
            for key, value in attributes.items()
        }
        info = InfoMetricFamily(name, description, labels=attributes)
        info.add_metric(labels=list(attributes.keys()), value=attributes)
        return info

    def _convert_exemplar(self, exemplar_data: Exemplar) -> PrometheusExemplar:
        """
        Converts the SDK exemplar into a Prometheus Exemplar, including proper time conversion.

        Parameters:
        - value (float): The value associated with the exemplar.
        - exemplar_data (ExemplarData): An OpenTelemetry exemplar data object containing attributes and timing information.

        Returns:
        - Exemplar: A Prometheus Exemplar object with correct labeling and timing.
        """
        labels = {
            sanitize_attribute(key): str(value)
            for key, value in exemplar_data.filtered_attributes.items()
        }

        # Add trace_id and span_id to labels only if they are valid and not None
        if (
            exemplar_data.trace_id is not None
            and exemplar_data.span_id is not None
        ):
            labels["trace_id"] = format_trace_id(exemplar_data.trace_id)
            labels["span_id"] = format_span_id(exemplar_data.span_id)

        # Convert time from nanoseconds to seconds
        timestamp_seconds = exemplar_data.time_unix_nano / 1e9
        prom_exemplar = PrometheusExemplar(
            labels, exemplar_data.value, timestamp_seconds
        )
        return prom_exemplar


class _AutoPrometheusMetricReader(PrometheusMetricReader):
    """Thin wrapper around PrometheusMetricReader used for the opentelemetry_metrics_exporter entry point.

    This allows users to use the prometheus exporter with opentelemetry-instrument. It handles
    starting the Prometheus http server on the the correct port and host.
    """

    def __init__(self) -> None:
        super().__init__()

        # Default values are specified in
        # https://github.com/open-telemetry/opentelemetry-specification/blob/v1.24.0/specification/configuration/sdk-environment-variables.md#prometheus-exporter
        start_http_server(
            port=int(environ.get(OTEL_EXPORTER_PROMETHEUS_PORT, "9464")),
            addr=environ.get(OTEL_EXPORTER_PROMETHEUS_HOST, "localhost"),
        )
