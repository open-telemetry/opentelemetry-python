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
    reader = PrometheusMetricReader(prefix=prefix)

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
from typing import (
    Any,
    Callable,
    Deque,
    Dict,
    Iterable,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

from prometheus_client import start_http_server
from prometheus_client.core import (
    REGISTRY,
    CounterMetricFamily,
    GaugeMetricFamily,
    HistogramMetricFamily,
    InfoMetricFamily,
)
from prometheus_client.core import Metric as PrometheusMetric

from opentelemetry.exporter.prometheus._mapping import (
    map_unit,
    sanitize_attribute,
    sanitize_full_name,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_PROMETHEUS_HOST,
    OTEL_EXPORTER_PROMETHEUS_PORT,
)
from opentelemetry.sdk.metrics import (
    Counter,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk.metrics import Histogram as HistogramInstrument
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    Gauge,
    Histogram,
    HistogramDataPoint,
    Metric,
    MetricReader,
    MetricsData,
    Sum,
)
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OtelComponentTypeValues,
)
from opentelemetry.util.types import Attributes, AttributeValue

_logger = getLogger(__name__)

_TARGET_INFO_NAME = "target"
_TARGET_INFO_DESCRIPTION = "Target metadata"

_OTEL_SCOPE_NAME_LABEL = "otel_scope_name"
_OTEL_SCOPE_VERSION_LABEL = "otel_scope_version"
_OTEL_SCOPE_SCHEMA_URL_LABEL = "otel_scope_schema_url"
_OTEL_SCOPE_ATTR_PREFIX = "otel_scope_"


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


def _should_convert_sum_to_gauge(metric: Metric) -> bool:
    # The Prometheus compatibility spec requires cumulative non-monotonic Sums
    # to be exported as Gauges.
    if not isinstance(metric.data, Sum):
        return False
    return (
        not metric.data.is_monotonic
        and metric.data.aggregation_temporality
        == AggregationTemporality.CUMULATIVE
    )


_FamilyT = TypeVar("_FamilyT", bound=PrometheusMetric)


def _get_or_create_family(
    registry: dict[str, PrometheusMetric],
    family_id: str,
    factory: Callable[..., _FamilyT],
    *,
    name: str,
    documentation: str,
    labels: Sequence[str],
    unit: str,
) -> _FamilyT:
    if family_id not in registry:
        registry[family_id] = factory(
            name=name,
            documentation=documentation,
            labels=labels,
            unit=unit,
        )
    return registry[family_id]


def _populate_counter_family(
    registry: dict[str, PrometheusMetric],
    per_metric_family_id: str,
    metric_name: str,
    description: str,
    unit: str,
    label_keys: Sequence[str],
    label_rows: Sequence[Sequence[str]],
    values: Sequence[float],
) -> None:
    family_id = "|".join([per_metric_family_id, CounterMetricFamily.__name__])
    family = _get_or_create_family(
        registry,
        family_id,
        CounterMetricFamily,
        name=metric_name,
        documentation=description,
        labels=label_keys,
        unit=unit,
    )
    for label_values, value in zip(label_rows, values):
        family.add_metric(labels=label_values, value=value)


def _populate_gauge_family(
    registry: dict[str, PrometheusMetric],
    per_metric_family_id: str,
    metric_name: str,
    description: str,
    unit: str,
    label_keys: Sequence[str],
    label_rows: Sequence[Sequence[str]],
    values: Sequence[float],
) -> None:
    family_id = "|".join([per_metric_family_id, GaugeMetricFamily.__name__])
    family = _get_or_create_family(
        registry,
        family_id,
        GaugeMetricFamily,
        name=metric_name,
        documentation=description,
        labels=label_keys,
        unit=unit,
    )
    for label_values, value in zip(label_rows, values):
        family.add_metric(labels=label_values, value=value)


def _populate_histogram_family(
    registry: dict[str, PrometheusMetric],
    per_metric_family_id: str,
    metric_name: str,
    description: str,
    unit: str,
    label_keys: Sequence[str],
    label_rows: Sequence[Sequence[str]],
    values: Sequence[dict[str, Any]],
) -> None:
    family_id = "|".join(
        [per_metric_family_id, HistogramMetricFamily.__name__]
    )
    family = _get_or_create_family(
        registry,
        family_id,
        HistogramMetricFamily,
        name=metric_name,
        documentation=description,
        labels=label_keys,
        unit=unit,
    )
    for label_values, value in zip(label_rows, values):
        family.add_metric(
            labels=label_values,
            buckets=_convert_buckets(
                value["bucket_counts"], value["explicit_bounds"]
            ),
            sum_value=value["sum"],
        )


class PrometheusMetricReader(MetricReader):
    """Prometheus metric exporter for OpenTelemetry.

    Args:
        disable_target_info: Whether to disable the ``target_info`` metric.
        without_scope_info: Whether to omit instrumentation scope labels from
            exported metrics. Scope labels are exported by default.
        prefix: Prefix added to exported Prometheus metric names.
    """

    def __init__(
        self,
        disable_target_info: bool = False,
        without_scope_info: bool = False,
        prefix: str = "",
    ) -> None:
        super().__init__(
            preferred_temporality={
                Counter: AggregationTemporality.CUMULATIVE,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                HistogramInstrument: AggregationTemporality.CUMULATIVE,
                ObservableCounter: AggregationTemporality.CUMULATIVE,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            },
            otel_component_type=OtelComponentTypeValues.PROMETHEUS_HTTP_TEXT_METRIC_EXPORTER,
        )
        self._collector = _CustomCollector(
            disable_target_info=disable_target_info,
            without_scope_info=without_scope_info,
            prefix=prefix,
        )
        REGISTRY.register(self._collector)
        self._collector._callback = self.collect
        self._prefix = prefix

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

    def __init__(
        self,
        disable_target_info: bool = False,
        without_scope_info: bool = False,
        prefix: str = "",
    ):
        self._callback = None
        self._metrics_datas: Deque[MetricsData] = deque()
        self._disable_target_info = disable_target_info
        self._without_scope_info = without_scope_info
        self._target_info = None
        self._prefix = prefix

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

    def _translate_to_prometheus(
        self,
        metrics_data: MetricsData,
        metric_family_id_metric_family: dict[str, PrometheusMetric],
    ):
        for rm in metrics_data.resource_metrics:
            for sm in rm.scope_metrics:
                scope_attrs = self._build_scope_attrs(sm.scope)
                for metric in sm.metrics:
                    self._translate_metric(
                        metric,
                        scope_attrs,
                        metric_family_id_metric_family,
                    )

    def _translate_metric(
        self,
        metric: Metric,
        scope_attrs: dict[str, Any],
        metric_family_id_metric_family: dict[str, PrometheusMetric],
    ) -> None:
        metric_name = self._resolve_metric_name(metric.name)
        description = metric.description or ""
        unit = map_unit(metric.unit or "")
        label_keys, label_rows, values = self._collect_data_points(
            metric, scope_attrs
        )
        per_metric_family_id = "|".join((metric_name, description, unit))

        convert_sum_to_gauge = _should_convert_sum_to_gauge(metric)

        if isinstance(metric.data, Sum) and not convert_sum_to_gauge:
            _populate_counter_family(
                metric_family_id_metric_family,
                per_metric_family_id,
                metric_name,
                description,
                unit,
                label_keys,
                label_rows,
                values,
            )
        elif isinstance(metric.data, Gauge) or convert_sum_to_gauge:
            _populate_gauge_family(
                metric_family_id_metric_family,
                per_metric_family_id,
                metric_name,
                description,
                unit,
                label_keys,
                label_rows,
                values,
            )
        elif isinstance(metric.data, Histogram):
            _populate_histogram_family(
                metric_family_id_metric_family,
                per_metric_family_id,
                metric_name,
                description,
                unit,
                label_keys,
                label_rows,
                values,
            )
        else:
            _logger.warning("Unsupported metric data. %s", type(metric.data))

    def _build_scope_attrs(
        self, scope: InstrumentationScope
    ) -> dict[str, AttributeValue]:
        if self._without_scope_info:
            return {}
        attrs: dict[str, AttributeValue] = {}
        if scope.attributes:
            for key, value in scope.attributes.items():
                attrs[_OTEL_SCOPE_ATTR_PREFIX + key] = value
        attrs[_OTEL_SCOPE_NAME_LABEL] = scope.name or ""
        attrs[_OTEL_SCOPE_VERSION_LABEL] = scope.version or ""
        attrs[_OTEL_SCOPE_SCHEMA_URL_LABEL] = scope.schema_url or ""
        return attrs

    def _resolve_metric_name(self, name: str) -> str:
        if self._prefix:
            name = self._prefix + "_" + name
        return sanitize_full_name(name)

    def _collect_data_points(
        self,
        metric: Metric,
        scope_attrs: dict[str, AttributeValue],
    ) -> tuple[list[str], list[list[str]], list[Any]]:
        keys: set[str] = set()
        rows: list[dict[str, str]] = []
        values: list = []

        for point in metric.data.data_points:
            labels: dict[str, str] = {}
            for key, value in chain(
                scope_attrs.items(),
                point.attributes.items(),
            ):
                label = sanitize_attribute(key)
                keys.add(label)
                labels[label] = self._check_value(value)
            rows.append(labels)

            if isinstance(point, HistogramDataPoint):
                values.append(
                    {
                        "bucket_counts": point.bucket_counts,
                        "explicit_bounds": point.explicit_bounds,
                        "sum": point.sum,
                    }
                )
            else:
                values.append(point.value)

        label_keys = sorted(keys)
        # Backfill missing labels with "" so every data point exposes the
        # full label set expected by the Prometheus family.
        label_rows = [
            [labels.get(k, "") for k in label_keys] for labels in rows
        ]
        return label_keys, label_rows, values

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
