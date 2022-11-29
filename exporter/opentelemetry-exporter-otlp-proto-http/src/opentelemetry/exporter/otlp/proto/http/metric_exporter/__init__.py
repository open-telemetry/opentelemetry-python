# Copyright The OpenTelemetry Authors
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

import gzip
import logging
import zlib
from os import environ
from typing import Dict, Optional, Sequence, Any, Callable, List, Mapping
from io import BytesIO
from time import sleep

from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.sdk.metrics._internal.aggregation import Aggregation
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import (
    AnyValue,
    ArrayValue,
    KeyValue,
    KeyValueList,
)
from opentelemetry.proto.common.v1.common_pb2 import InstrumentationScope
from opentelemetry.proto.resource.v1.resource_pb2 import Resource
from opentelemetry.proto.metrics.v1 import metrics_pb2 as pb2
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_TIMEOUT,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
    OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_HEADERS,
    OTEL_EXPORTER_OTLP_METRICS_TIMEOUT,
    OTEL_EXPORTER_OTLP_METRICS_COMPRESSION,
)
from opentelemetry.sdk.metrics import (
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    Gauge,
    Histogram as HistogramType,
    MetricExporter,
    MetricExportResult,
    MetricsData,
    Sum,
)
from opentelemetry.sdk.resources import Resource as SDKResource
from opentelemetry.util.re import parse_env_headers

import backoff
import requests

_logger = logging.getLogger(__name__)


DEFAULT_COMPRESSION = Compression.NoCompression
DEFAULT_ENDPOINT = "http://localhost:4318/"
DEFAULT_METRICS_EXPORT_PATH = "v1/metrics"
DEFAULT_TIMEOUT = 10  # in seconds

# Work around API change between backoff 1.x and 2.x. Since 2.0.0 the backoff
# wait generator API requires a first .send(None) before reading the backoff
# values from the generator.
_is_backoff_v2 = next(backoff.expo()) is None


def _expo(*args, **kwargs):
    gen = backoff.expo(*args, **kwargs)
    if _is_backoff_v2:
        gen.send(None)
    return gen


class OTLPMetricExporter(MetricExporter):

    _MAX_RETRY_TIMEOUT = 64

    def __init__(
        self,
        endpoint: Optional[str] = None,
        certificate_file: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        compression: Optional[Compression] = None,
        session: Optional[requests.Session] = None,
        preferred_temporality: Dict[type, AggregationTemporality] = None,
        preferred_aggregation: Dict[type, Aggregation] = None,
    ):
        self._endpoint = endpoint or environ.get(
            OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
            _append_metrics_path(
                environ.get(OTEL_EXPORTER_OTLP_ENDPOINT, DEFAULT_ENDPOINT)
            ),
        )
        self._certificate_file = certificate_file or environ.get(
            OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
            environ.get(OTEL_EXPORTER_OTLP_CERTIFICATE, True),
        )
        headers_string = environ.get(
            OTEL_EXPORTER_OTLP_METRICS_HEADERS,
            environ.get(OTEL_EXPORTER_OTLP_HEADERS, ""),
        )
        self._headers = headers or parse_env_headers(headers_string)
        self._timeout = timeout or int(
            environ.get(
                OTEL_EXPORTER_OTLP_METRICS_TIMEOUT,
                environ.get(OTEL_EXPORTER_OTLP_TIMEOUT, DEFAULT_TIMEOUT),
            )
        )
        self._compression = compression or _compression_from_env()
        self._session = session or requests.Session()
        self._session.headers.update(self._headers)
        self._session.headers.update(
            {"Content-Type": "application/x-protobuf"}
        )
        if self._compression is not Compression.NoCompression:
            self._session.headers.update(
                {"Content-Encoding": self._compression.value}
            )

        instrument_class_temporality = {}
        if (
            environ.get(
                OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
                "CUMULATIVE",
            )
            .upper()
            .strip()
            == "DELTA"
        ):
            instrument_class_temporality = {
                Counter: AggregationTemporality.DELTA,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                Histogram: AggregationTemporality.DELTA,
                ObservableCounter: AggregationTemporality.DELTA,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }
        else:
            instrument_class_temporality = {
                Counter: AggregationTemporality.CUMULATIVE,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                Histogram: AggregationTemporality.CUMULATIVE,
                ObservableCounter: AggregationTemporality.CUMULATIVE,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }
        instrument_class_temporality.update(preferred_temporality or {})

        MetricExporter.__init__(
            self,
            preferred_temporality=instrument_class_temporality,
            preferred_aggregation=preferred_aggregation,
        )

    def _export(self, serialized_data: str):
        data = serialized_data
        if self._compression == Compression.Gzip:
            gzip_data = BytesIO()
            with gzip.GzipFile(fileobj=gzip_data, mode="w") as gzip_stream:
                gzip_stream.write(serialized_data)
            data = gzip_data.getvalue()
        elif self._compression == Compression.Deflate:
            data = zlib.compress(bytes(serialized_data))

        return self._session.post(
            url=self._endpoint,
            data=data,
            verify=self._certificate_file,
            timeout=self._timeout,
        )

    @staticmethod
    def _retryable(resp: requests.Response) -> bool:
        if resp.status_code == 408:
            return True
        if resp.status_code >= 500 and resp.status_code <= 599:
            return True
        return False

    def _translate_data(
        self, data: MetricsData
    ) -> ExportMetricsServiceRequest:

        resource_metrics_dict = {}

        for resource_metrics in data.resource_metrics:

            resource = resource_metrics.resource

            # It is safe to assume that each entry in data.resource_metrics is
            # associated with an unique resource.
            scope_metrics_dict = {}

            resource_metrics_dict[resource] = scope_metrics_dict

            for scope_metrics in resource_metrics.scope_metrics:

                instrumentation_scope = scope_metrics.scope

                # The SDK groups metrics in instrumentation scopes already so
                # there is no need to check for existing instrumentation scopes
                # here.
                pb2_scope_metrics = pb2.ScopeMetrics(
                    scope=InstrumentationScope(
                        name=instrumentation_scope.name,
                        version=instrumentation_scope.version,
                    )
                )

                scope_metrics_dict[instrumentation_scope] = pb2_scope_metrics

                for metric in scope_metrics.metrics:
                    pb2_metric = pb2.Metric(
                        name=metric.name,
                        description=metric.description,
                        unit=metric.unit,
                    )

                    if isinstance(metric.data, Gauge):
                        for data_point in metric.data.data_points:
                            pt = pb2.NumberDataPoint(
                                attributes=self._translate_attributes(
                                    data_point.attributes
                                ),
                                time_unix_nano=data_point.time_unix_nano,
                            )
                            if isinstance(data_point.value, int):
                                pt.as_int = data_point.value
                            else:
                                pt.as_double = data_point.value
                            pb2_metric.gauge.data_points.append(pt)

                    elif isinstance(metric.data, HistogramType):
                        for data_point in metric.data.data_points:
                            pt = pb2.HistogramDataPoint(
                                attributes=self._translate_attributes(
                                    data_point.attributes
                                ),
                                time_unix_nano=data_point.time_unix_nano,
                                start_time_unix_nano=(
                                    data_point.start_time_unix_nano
                                ),
                                count=data_point.count,
                                sum=data_point.sum,
                                bucket_counts=data_point.bucket_counts,
                                explicit_bounds=data_point.explicit_bounds,
                                max=data_point.max,
                                min=data_point.min,
                            )
                            pb2_metric.histogram.aggregation_temporality = (
                                metric.data.aggregation_temporality
                            )
                            pb2_metric.histogram.data_points.append(pt)

                    elif isinstance(metric.data, Sum):
                        for data_point in metric.data.data_points:
                            pt = pb2.NumberDataPoint(
                                attributes=self._translate_attributes(
                                    data_point.attributes
                                ),
                                start_time_unix_nano=(
                                    data_point.start_time_unix_nano
                                ),
                                time_unix_nano=data_point.time_unix_nano,
                            )
                            if isinstance(data_point.value, int):
                                pt.as_int = data_point.value
                            else:
                                pt.as_double = data_point.value
                            # note that because sum is a message type, the
                            # fields must be set individually rather than
                            # instantiating a pb2.Sum and setting it once
                            pb2_metric.sum.aggregation_temporality = (
                                metric.data.aggregation_temporality
                            )
                            pb2_metric.sum.is_monotonic = (
                                metric.data.is_monotonic
                            )
                            pb2_metric.sum.data_points.append(pt)
                    else:
                        _logger.warn(
                            "unsupported datapoint type %s", metric.point
                        )
                        continue

                    pb2_scope_metrics.metrics.append(pb2_metric)

        return ExportMetricsServiceRequest(
            resource_metrics=get_resource_data(
                resource_metrics_dict,
                pb2.ResourceMetrics,
                "metrics",
            )
        )

    def _translate_attributes(self, attributes) -> Sequence[KeyValue]:
        output = []
        if attributes:

            for key, value in attributes.items():
                try:
                    output.append(_translate_key_values(key, value))
                except Exception as error:  # pylint: disable=broad-except
                    _logger.exception(error)
        return output

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        serialized_data = self._translate_data(metrics_data)
        for delay in _expo(max_value=self._MAX_RETRY_TIMEOUT):

            if delay == self._MAX_RETRY_TIMEOUT:
                return MetricExportResult.FAILURE

            resp = self._export(serialized_data.SerializeToString())
            # pylint: disable=no-else-return
            if resp.status_code in (200, 202):
                return MetricExportResult.SUCCESS
            elif self._retryable(resp):
                _logger.warning(
                    "Transient error %s encountered while exporting metric batch, retrying in %ss.",
                    resp.reason,
                    delay,
                )
                sleep(delay)
                continue
            else:
                _logger.error(
                    "Failed to export batch code: %s, reason: %s",
                    resp.status_code,
                    resp.text,
                )
                return MetricExportResult.FAILURE
        return MetricExportResult.FAILURE

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        pass

    @property
    def _exporting(self) -> str:
        return "metrics"

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return True


def _translate_value(value: Any) -> KeyValue:

    if isinstance(value, bool):
        any_value = AnyValue(bool_value=value)

    elif isinstance(value, str):
        any_value = AnyValue(string_value=value)

    elif isinstance(value, int):
        any_value = AnyValue(int_value=value)

    elif isinstance(value, float):
        any_value = AnyValue(double_value=value)

    elif isinstance(value, Sequence):
        any_value = AnyValue(
            array_value=ArrayValue(values=[_translate_value(v) for v in value])
        )

    elif isinstance(value, Mapping):
        any_value = AnyValue(
            kvlist_value=KeyValueList(
                values=[
                    _translate_key_values(str(k), v) for k, v in value.items()
                ]
            )
        )

    else:
        raise Exception(f"Invalid type {type(value)} of value {value}")

    return any_value


def _translate_key_values(key: str, value: Any) -> KeyValue:
    return KeyValue(key=key, value=_translate_value(value))


def get_resource_data(
    sdk_resource_scope_data: Dict[SDKResource, Any],  # ResourceDataT?
    resource_class: Callable[..., Resource],
    name: str,
) -> List[Resource]:

    resource_data = []

    for (
        sdk_resource,
        scope_data,
    ) in sdk_resource_scope_data.items():

        collector_resource = Resource()

        for key, value in sdk_resource.attributes.items():

            try:
                # pylint: disable=no-member
                collector_resource.attributes.append(
                    _translate_key_values(key, value)
                )
            except Exception as error:  # pylint: disable=broad-except
                _logger.exception(error)

        resource_data.append(
            resource_class(
                **{
                    "resource": collector_resource,
                    "scope_{}".format(name): scope_data.values(),
                }
            )
        )

    return resource_data


def _compression_from_env() -> Compression:
    compression = (
        environ.get(
            OTEL_EXPORTER_OTLP_METRICS_COMPRESSION,
            environ.get(OTEL_EXPORTER_OTLP_COMPRESSION, "none"),
        )
        .lower()
        .strip()
    )
    return Compression(compression)


def _append_metrics_path(endpoint: str) -> str:
    if endpoint.endswith("/"):
        return endpoint + DEFAULT_METRICS_EXPORT_PATH
    return endpoint + f"/{DEFAULT_METRICS_EXPORT_PATH}"
