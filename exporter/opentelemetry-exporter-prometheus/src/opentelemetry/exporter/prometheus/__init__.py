# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

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
from collections.abc import Callable, Iterable, Mapping, Sequence
from itertools import chain
from json import dumps
from logging import getLogger
from os import environ
from typing import Any

from prometheus_client import CollectorRegistry, start_http_server
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
    CardinalityLimits,
    DataT,
    Gauge,
    Histogram,
    HistogramDataPoint,
    Metric,
    MetricReader,
    MetricsData,
    Sum,
)
from opentelemetry.sdk.metrics.view import Aggregation
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OtelComponentTypeValues,
)
from opentelemetry.util.types import AnyValue, Attributes

_logger = getLogger(__name__)

_TARGET_INFO_NAME = "target"
_TARGET_INFO_DESCRIPTION = "Target metadata"

_DEFAULT_PORT = 9464


def _port_from_env() -> int:
    """Return ``OTEL_EXPORTER_PROMETHEUS_PORT`` as an int, defaulting to
    ``_DEFAULT_PORT`` when the variable is unset, empty, or not an integer.

    An invalid value is logged and ignored instead of raising, mirroring the
    OTLP/Zipkin exporters so a malformed environment variable cannot take
    auto-instrumentation startup down.
    """
    raw = environ.get(OTEL_EXPORTER_PROMETHEUS_PORT)
    if raw is None or not raw.strip():
        return _DEFAULT_PORT
    try:
        return int(raw)
    except ValueError:
        _logger.warning(
            "Invalid value %r for %s, using default port %s",
            raw,
            OTEL_EXPORTER_PROMETHEUS_PORT,
            _DEFAULT_PORT,
        )
        return _DEFAULT_PORT


_OTEL_SCOPE_NAME_LABEL = "otel_scope_name"
_OTEL_SCOPE_VERSION_LABEL = "otel_scope_version"
_OTEL_SCOPE_SCHEMA_URL_LABEL = "otel_scope_schema_url"
_OTEL_SCOPE_ATTR_PREFIX = "otel_scope_"


def _convert_buckets(bucket_counts: Sequence[int], explicit_bounds: Sequence[float]) -> Sequence[tuple[str, int]]:
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
    return not metric.data.is_monotonic and metric.data.aggregation_temporality == AggregationTemporality.CUMULATIVE


_MetricFamilyFactory = type[CounterMetricFamily] | type[GaugeMetricFamily] | type[HistogramMetricFamily]


class _PendingMetricFamily:
    """Accumulates data points across metrics that share a Prometheus family."""

    def __init__(
        self,
        factory: _MetricFamilyFactory,
        name: str,
        description: str,
        unit: str,
    ) -> None:
        self.factory = factory
        self.name = name
        self.description = description
        self.unit = unit
        self.keys: set[str] = set()
        self.rows: list[dict[str, str]] = []
        self.values: list[float | dict[str, Any]] = []

    def add_points(
        self,
        keys: set[str],
        rows: Sequence[dict[str, str]],
        values: Sequence[float | dict[str, Any]],
    ) -> None:
        self.keys.update(keys)
        self.rows.extend(rows)
        self.values.extend(values)

    def build(self) -> PrometheusMetric:
        label_keys = sorted(self.keys)
        family = self.factory(
            name=self.name,
            documentation=self.description,
            labels=label_keys,
            unit=self.unit,
        )
        # Backfill missing labels with "" after collecting every metric in the
        # family so points from different instruments stay aligned by name.
        if isinstance(family, HistogramMetricFamily):
            for row, value in zip(self.rows, self.values):
                if isinstance(value, dict):
                    family.add_metric(
                        labels=[row.get(k, "") for k in label_keys],
                        buckets=_convert_buckets(value["bucket_counts"], value["explicit_bounds"]),
                        sum_value=value["sum"],
                    )
        else:
            for row, value in zip(self.rows, self.values):
                if not isinstance(value, dict):
                    family.add_metric(
                        labels=[row.get(k, "") for k in label_keys],
                        value=value,
                    )
        return family


class PrometheusMetricReader(MetricReader):
    """Prometheus metric exporter for OpenTelemetry.

    Args:
        disable_target_info: Whether to disable the ``target_info`` metric.
        prefix: Prefix added to exported Prometheus metric names.
        scope_info_enabled: Whether to include instrumentation scope labels on
            exported metrics. Scope labels are exported by default.
        preferred_aggregation: A mapping between instrument classes and
            aggregation instances used to override the default aggregation of
            the corresponding instrument classes. Classes not included in the
            mapping retain their default aggregation. See
            :class:`~opentelemetry.sdk.metrics.export.MetricReader` for details.
        resource_attribute_filter: Optional callback to select resource attributes
            that are copied as labels on exported metrics. The callback receives
            the original resource attribute key. Selected keys are sanitized to
            valid Prometheus label names.
        cardinality_limits: A mapping between instrument classes and the
            maximum number of metric points a metric stream of that class may
            export per collection cycle. Classes not included in the mapping
            use a limit of 2000. See
            :class:`~opentelemetry.sdk.metrics.export.MetricReader` for details.
    """

    def __init__(
        self,
        disable_target_info: bool = False,
        prefix: str = "",
        scope_info_enabled: bool = True,
        preferred_aggregation: Mapping[type, Aggregation] | None = None,
        *,
        resource_attribute_filter: Callable[[str], bool] | None = None,
        registry: CollectorRegistry = REGISTRY,
        cardinality_limits: CardinalityLimits | None = None,
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
            preferred_aggregation=dict(preferred_aggregation) if preferred_aggregation is not None else None,
            cardinality_limits=cardinality_limits,
            otel_component_type=OtelComponentTypeValues.PROMETHEUS_HTTP_TEXT_METRIC_EXPORTER,
        )
        self._collector = _CustomCollector(
            disable_target_info=disable_target_info,
            prefix=prefix,
            scope_info_enabled=scope_info_enabled,
            resource_attribute_filter=resource_attribute_filter,
        )
        self._registry = registry
        self._registry.register(self._collector)
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
        self._registry.unregister(self._collector)


class _CustomCollector:
    """_CustomCollector represents the Prometheus Collector object

    See more:
    https://github.com/prometheus/client_python#custom-collectors
    """

    def __init__(
        self,
        disable_target_info: bool = False,
        prefix: str = "",
        scope_info_enabled: bool = True,
        resource_attribute_filter: Callable[[str], bool] | None = None,
    ):
        self._callback = None
        self._metrics_datas: deque[MetricsData] = deque()
        self._disable_target_info = disable_target_info
        self._target_info = None
        self._prefix = prefix
        self._scope_info_enabled = scope_info_enabled
        self._resource_attribute_filter = resource_attribute_filter

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

        metric_family_id_metric_family: dict[str, PrometheusMetric] = {}
        pending_families: dict[str, _PendingMetricFamily] = {}

        if len(self._metrics_datas):
            if not self._disable_target_info:
                if self._target_info is None:
                    attributes: Attributes = {}
                    for res in self._metrics_datas[0].resource_metrics:
                        attributes = {**attributes, **res.resource.attributes}

                    self._target_info = self._create_info_metric(
                        _TARGET_INFO_NAME, _TARGET_INFO_DESCRIPTION, attributes
                    )
                metric_family_id_metric_family[_TARGET_INFO_NAME] = self._target_info

        while self._metrics_datas:
            self._translate_to_prometheus(self._metrics_datas.popleft(), pending_families)

        for family_id, pending in pending_families.items():
            metric_family_id_metric_family[family_id] = pending.build()

        if metric_family_id_metric_family:
            yield from metric_family_id_metric_family.values()

    def _translate_to_prometheus(
        self,
        metrics_data: MetricsData,
        pending_families: dict[str, _PendingMetricFamily],
    ) -> None:
        for rm in metrics_data.resource_metrics:
            resource_attrs = self._build_resource_attrs(rm.resource)
            for sm in rm.scope_metrics:
                scope_attrs = self._build_scope_attrs(sm.scope)
                for metric in sm.metrics:
                    self._translate_metric(
                        metric=metric,
                        scope_attrs=scope_attrs,
                        resource_attrs=resource_attrs,
                        pending_families=pending_families,
                    )

    def _translate_metric(
        self,
        metric: Metric,
        scope_attrs: dict[str, AnyValue],
        resource_attrs: dict[str, AnyValue],
        pending_families: dict[str, _PendingMetricFamily],
    ) -> None:
        metric_name = self._resolve_metric_name(metric.name)
        description = metric.description or ""
        unit = map_unit(metric.unit or "")
        convert_sum_to_gauge = _should_convert_sum_to_gauge(metric)

        factory: _MetricFamilyFactory
        if isinstance(metric.data, Sum) and not convert_sum_to_gauge:
            factory = CounterMetricFamily
        elif isinstance(metric.data, Gauge) or convert_sum_to_gauge:
            factory = GaugeMetricFamily
        elif isinstance(metric.data, Histogram):
            factory = HistogramMetricFamily
        else:
            _logger.warning("Unsupported metric data. %s", type(metric.data))
            return

        keys, rows, values = self._collect_data_points(metric.data, scope_attrs, resource_attrs)
        family_id = "|".join((metric_name, description, unit, factory.__name__))
        pending = pending_families.get(family_id)
        if pending is None:
            pending = _PendingMetricFamily(
                factory=factory,
                name=metric_name,
                description=description,
                unit=unit,
            )
            pending_families[family_id] = pending
        pending.add_points(keys, rows, values)

    def _build_scope_attrs(self, scope: InstrumentationScope) -> dict[str, AnyValue]:
        if not self._scope_info_enabled:
            return {}
        attrs: dict[str, AnyValue] = {}
        if scope.attributes:
            for key, value in scope.attributes.items():
                attrs[_OTEL_SCOPE_ATTR_PREFIX + key] = value
        attrs[_OTEL_SCOPE_NAME_LABEL] = scope.name or ""
        attrs[_OTEL_SCOPE_VERSION_LABEL] = scope.version or ""
        attrs[_OTEL_SCOPE_SCHEMA_URL_LABEL] = scope.schema_url or ""
        return attrs

    def _build_resource_attrs(self, resource: Resource) -> dict[str, AnyValue]:
        if not self._resource_attribute_filter:
            return {}
        return {key: value for key, value in resource.attributes.items() if self._resource_attribute_filter(key)}

    def _resolve_metric_name(self, name: str) -> str:
        if self._prefix:
            name = self._prefix + "_" + name
        return sanitize_full_name(name)

    def _collect_data_points(
        self,
        metric_data: DataT,
        scope_attrs: dict[str, AnyValue],
        resource_attrs: dict[str, AnyValue],
    ) -> tuple[set[str], list[dict[str, str]], list[float | dict[str, Any]]]:
        keys: set[str] = set()
        rows: list[dict[str, str]] = []
        values: list[float | dict[str, Any]] = []

        for point in metric_data.data_points:
            labels: dict[str, str] = {}
            for key, value in chain(
                resource_attrs.items(),
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

        return keys, rows, values

    # pylint: disable=no-self-use
    def _check_value(self, value: float | str | Sequence) -> str:
        """Check the label value and return is appropriate representation"""
        if not isinstance(value, str):
            return dumps(value, default=str)
        return str(value)

    def _create_info_metric(self, name: str, description: str, attributes: dict[str, str]) -> InfoMetricFamily:
        """Create an Info Metric Family with list of attributes"""
        # sanitize the attribute names according to Prometheus rule
        attributes = {sanitize_attribute(key): self._check_value(value) for key, value in attributes.items()}
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
            port=_port_from_env(),
            addr=environ.get(OTEL_EXPORTER_PROMETHEUS_HOST, "localhost"),
        )
