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
from __future__ import annotations

import gzip
import logging
import zlib
from io import BytesIO
from os import environ
from time import sleep
from typing import (  # noqa: F401
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Sequence,
)

import requests
from deprecated import deprecated
from requests.exceptions import ConnectionError

from opentelemetry.exporter.otlp.proto.common._internal import (
    _create_exp_backoff_generator,
    _get_resource_data,
)
from opentelemetry.exporter.otlp.proto.common._internal.metrics_encoder import (
    OTLPMetricExporterMixin,
)
from opentelemetry.exporter.otlp.proto.common.metrics_encoder import (
    encode_metrics,
)
from opentelemetry.exporter.otlp.proto.http import (
    _OTLP_HTTP_HEADERS,
    Compression,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (  # noqa: F401
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import (  # noqa: F401  # noqa: F401
    AnyValue,
    ArrayValue,
    InstrumentationScope,
    KeyValue,
    KeyValueList,
)
from opentelemetry.proto.metrics.v1 import metrics_pb2 as pb2  # noqa: F401
from opentelemetry.proto.resource.v1.resource_pb2 import Resource  # noqa: F401
from opentelemetry.proto.resource.v1.resource_pb2 import (
    Resource as PB2Resource,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_METRICS_COMPRESSION,
    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
    OTEL_EXPORTER_OTLP_METRICS_HEADERS,
    OTEL_EXPORTER_OTLP_METRICS_TIMEOUT,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.sdk.metrics._internal.aggregation import Aggregation
from opentelemetry.sdk.metrics.export import (  # noqa: F401
    AggregationTemporality,
    Gauge,
    MetricExporter,
    MetricExportResult,
    MetricsData,
    Sum,
)
from opentelemetry.sdk.metrics.export import (  # noqa: F401
    Histogram as HistogramType,
)
from opentelemetry.sdk.resources import Resource as SDKResource
from opentelemetry.util.re import parse_env_headers

_logger = logging.getLogger(__name__)


DEFAULT_COMPRESSION = Compression.NoCompression
DEFAULT_ENDPOINT = "http://localhost:4318/"
DEFAULT_METRICS_EXPORT_PATH = "v1/metrics"
DEFAULT_TIMEOUT = 10  # in seconds


class OTLPMetricExporter(MetricExporter, OTLPMetricExporterMixin):
    _MAX_RETRY_TIMEOUT = 64

    def __init__(
        self,
        endpoint: str | None = None,
        certificate_file: str | None = None,
        client_key_file: str | None = None,
        client_certificate_file: str | None = None,
        headers: dict[str, str] | None = None,
        timeout: int | None = None,
        compression: Compression | None = None,
        session: requests.Session | None = None,
        preferred_temporality: dict[type, AggregationTemporality]
        | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
        max_export_batch_size: int | None = None,
    ):
        """OTLP HTTP metrics exporter

        Args:
            endpoint: Target URL to which the exporter is going to send metrics
            certificate_file: Path to the certificate file to use for any TLS
            client_key_file: Path to the client key file to use for any TLS
            client_certificate_file: Path to the client certificate file to use for any TLS
            headers: Headers to be sent with HTTP requests at export
            timeout: Timeout in seconds for export
            compression: Compression to use; one of none, gzip, deflate
            session: Requests session to use at export
            preferred_temporality: Map of preferred temporality for each metric type.
                See `opentelemetry.sdk.metrics.export.MetricReader` for more details on what
                preferred temporality is.
            preferred_aggregation: Map of preferred aggregation for each metric type.
                See `opentelemetry.sdk.metrics.export.MetricReader` for more details on what
                preferred aggregation is.
            max_export_batch_size: Maximum number of data points to export in a single request.
                If not set there is no limit to the number of data points in a request.
                If it is set and the number of data points exceeds the max, the request will be split.
        """
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
        self._client_key_file = client_key_file or environ.get(
            OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY,
            environ.get(OTEL_EXPORTER_OTLP_CLIENT_KEY, None),
        )
        self._client_certificate_file = client_certificate_file or environ.get(
            OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE,
            environ.get(OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE, None),
        )
        self._client_cert = (
            (self._client_certificate_file, self._client_key_file)
            if self._client_certificate_file and self._client_key_file
            else self._client_certificate_file
        )
        headers_string = environ.get(
            OTEL_EXPORTER_OTLP_METRICS_HEADERS,
            environ.get(OTEL_EXPORTER_OTLP_HEADERS, ""),
        )
        self._headers = headers or parse_env_headers(
            headers_string, liberal=True
        )
        self._timeout = timeout or int(
            environ.get(
                OTEL_EXPORTER_OTLP_METRICS_TIMEOUT,
                environ.get(OTEL_EXPORTER_OTLP_TIMEOUT, DEFAULT_TIMEOUT),
            )
        )
        self._compression = compression or _compression_from_env()
        self._session = session or requests.Session()
        self._session.headers.update(self._headers)
        self._session.headers.update(_OTLP_HTTP_HEADERS)
        if self._compression is not Compression.NoCompression:
            self._session.headers.update(
                {"Content-Encoding": self._compression.value}
            )

        self._common_configuration(
            preferred_temporality, preferred_aggregation
        )
        self._max_export_batch_size: int | None = max_export_batch_size

    def _export(self, serialized_data: bytes):
        data = serialized_data
        if self._compression == Compression.Gzip:
            gzip_data = BytesIO()
            with gzip.GzipFile(fileobj=gzip_data, mode="w") as gzip_stream:
                gzip_stream.write(serialized_data)
            data = gzip_data.getvalue()
        elif self._compression == Compression.Deflate:
            data = zlib.compress(serialized_data)

        # By default, keep-alive is enabled in Session's request
        # headers. Backends may choose to close the connection
        # while a post happens which causes an unhandled
        # exception. This try/except will retry the post on such exceptions
        try:
            resp = self._session.post(
                url=self._endpoint,
                data=data,
                verify=self._certificate_file,
                timeout=self._timeout,
                cert=self._client_cert,
            )
        except ConnectionError:
            resp = self._session.post(
                url=self._endpoint,
                data=data,
                verify=self._certificate_file,
                timeout=self._timeout,
                cert=self._client_cert,
            )
        return resp

    @staticmethod
    def _retryable(resp: requests.Response) -> bool:
        if resp.status_code == 408:
            return True
        if resp.status_code >= 500 and resp.status_code <= 599:
            return True
        return False

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        serialized_data = encode_metrics(metrics_data)
        for delay in _create_exp_backoff_generator(
            max_value=self._MAX_RETRY_TIMEOUT
        ):
            if delay == self._MAX_RETRY_TIMEOUT:
                return MetricExportResult.FAILURE

            if self._max_export_batch_size is None:
                resp = self._export(serialized_data.SerializeToString())
                # pylint: disable=no-else-return
                if resp.ok:
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
            
            # Else, attempt export in batches for this retry
            else:
                export_result = MetricExportResult.SUCCESS
                for split_metrics_data in self._split_metrics_data(serialized_data):
                    split_resp = self._export(
                        split_metrics_data.SerializeToString()
                    )

                    if split_resp.ok:
                        export_result = MetricExportResult.SUCCESS
                    elif self._retryable(split_resp):
                        _logger.warning(
                            "Transient error %s encountered while exporting metric batch, retrying in %ss.",
                            split_resp.reason,
                            delay,
                        )
                        sleep(delay)
                        continue
                    else:
                        _logger.error(
                            "Failed to export batch code: %s, reason: %s",
                            split_resp.status_code,
                            split_resp.text,
                        )
                        export_result = MetricExportResult.FAILURE
                
                # Return result after all batches are attempted
                return export_result
    
        return MetricExportResult.FAILURE

    def _split_metrics_data(
        self,
        metrics_data: pb2.MetricsData,
    ) -> Iterable[pb2.MetricsData]:
        """Splits metrics data into several MetricsData (copies protobuf originals), 
        based on configured data point max export batch size.

        Args:
            metrics_data: metrics object based on HTTP protocol buffer definition

        Returns:
            Iterable[pb2.MetricsData]: An iterable of pb2.MetricsData objects containing
                pb2.ResourceMetrics, pb2.ScopeMetrics, pb2.Metrics, and data points
        """
        batch_size: int = 0
        # Stores split metrics data as editable references
        # used to write batched pb2 objects for export when finalized
        split_resource_metrics = []

        for resource_metrics in metrics_data.resource_metrics:
            split_scope_metrics = []
            split_resource_metrics.append(
                {
                    "resource": resource_metrics.resource,
                    "schema_url": resource_metrics.schema_url,
                    "scope_metrics": split_scope_metrics,
                }
            )

            for scope_metrics in resource_metrics.scope_metrics:
                split_metrics = []
                split_scope_metrics.append(
                    {
                        "scope": scope_metrics.scope,
                        "schema_url": scope_metrics.schema_url,
                        "metrics": split_metrics,
                    }
                )

                for metric in scope_metrics.metrics:
                    split_data_points = []

                    # protobuf specifies metrics types (e.g. Sum, Histogram)
                    # with different accessors for data points, etc
                    # We maintain these structures throughout batch calculation
                    current_data_points = []
                    if metric.HasField("sum"):
                        split_metrics.append(
                            {
                                "name": metric.name,
                                "description": metric.description,
                                "unit": metric.unit,
                                "sum": {
                                    "aggregation_temporality": metric.sum.aggregation_temporality,
                                    "is_monotonic": metric.sum.is_monotonic,
                                    "data_points": split_data_points,
                                }
                            }
                        )
                        current_data_points = metric.sum.data_points
                    elif metric.HasField("histogram"):
                        split_metrics.append(
                            {
                                "name": metric.name,
                                "description": metric.description,
                                "unit": metric.unit,
                                "histogram": {
                                    "aggregation_temporality": metric.histogram.aggregation_temporality,
                                    "data_points": split_data_points,
                                }
                            }
                        )
                        current_data_points = metric.histogram.data_points
                    elif metric.HasField("exponential_histogram"):
                        split_metrics.append(
                            {
                                "name": metric.name,
                                "description": metric.description,
                                "unit": metric.unit,
                                "exponential_histogram": {
                                    "aggregation_temporality": metric.exponential_histogram.aggregation_temporality,
                                    "data_points": split_data_points,
                                }
                            }
                        )
                        current_data_points = metric.exponential_histogram.data_points
                    elif metric.HasField("gauge"):
                        split_metrics.append(
                            {
                                "name": metric.name,
                                "description": metric.description,
                                "unit": metric.unit,
                                "gauge": {
                                    "data_points": split_data_points,
                                }
                            }
                        )
                        current_data_points = metric.gauge.data_points
                    elif metric.HasField("summary"):
                        split_metrics.append(
                            {
                                "name": metric.name,
                                "description": metric.description,
                                "unit": metric.unit,
                                "summary": {
                                    "data_points": split_data_points,
                                }
                            }
                        )
                    else:
                        _logger.warning("Tried to split and export an unsupported metric type. Skipping.")
                        continue

                    for data_point in current_data_points:
                        split_data_points.append(data_point)
                        batch_size += 1

                        if batch_size >= self._max_export_batch_size:
                            yield pb2.MetricsData(
                                resource_metrics=self._get_split_resource_metrics_pb2(split_resource_metrics)
                            )

                            # Reset all the reference variables with current metrics_data position
                            # minus yielded data_points. Need to clear data_points and keep metric
                            # to avoid duplicate data_point export
                            batch_size = 0
                            split_data_points = []

                            if metric.HasField("sum"):
                                split_metrics = [
                                    {
                                        "name": metric.name,
                                        "description": metric.description,
                                        "unit": metric.unit,
                                        "sum": {
                                            "aggregation_temporality": metric.sum.aggregation_temporality,
                                            "is_monotonic": metric.sum.is_monotonic,
                                            "data_points": split_data_points,
                                        }
                                    }
                                ]
                            elif metric.HasField("histogram"):
                                split_metrics = [
                                    {
                                        "name": metric.name,
                                        "description": metric.description,
                                        "unit": metric.unit,
                                        "histogram": {
                                            "aggregation_temporality": metric.histogram.aggregation_temporality,
                                            "data_points": split_data_points,
                                        }
                                    }
                                ]
                            elif metric.HasField("exponential_histogram"):
                                split_metrics = [
                                    {
                                        "name": metric.name,
                                        "description": metric.description,
                                        "unit": metric.unit,
                                        "exponential_histogram": {
                                            "aggregation_temporality": metric.exponential_histogram.aggregation_temporality,
                                            "data_points": split_data_points,
                                        }
                                    }
                                ]
                            elif metric.HasField("gauge"):
                                split_metrics = [
                                    {
                                        "name": metric.name,
                                        "description": metric.description,
                                        "unit": metric.unit,
                                        "gauge": {
                                            "data_points": split_data_points,
                                        }
                                    }
                                ]
                            elif metric.HasField("summary"):
                                split_metrics = [
                                    {
                                        "name": metric.name,
                                        "description": metric.description,
                                        "unit": metric.unit,
                                        "summary": {
                                            "data_points": split_data_points,
                                        }
                                    }
                                ]

                            split_scope_metrics = [
                                {
                                    "scope": scope_metrics.scope,
                                    "schema_url": scope_metrics.schema_url,
                                    "metrics": split_metrics,
                                }
                            ]
                            split_resource_metrics = [
                                {
                                    "resource": resource_metrics.resource,
                                    "schema_url": resource_metrics.schema_url,
                                    "scope_metrics": split_scope_metrics,
                                }
                            ]

                    if not split_data_points:
                        # If data_points is empty remove the whole metric
                        split_metrics.pop()

                if not split_metrics:
                    # If metrics is empty remove the whole scope_metrics
                    split_scope_metrics.pop()

            if not split_scope_metrics:
                # If scope_metrics is empty remove the whole resource_metrics
                split_resource_metrics.pop()

        if batch_size > 0:
            yield pb2.MetricsData(
                resource_metrics=self._get_split_resource_metrics_pb2(split_resource_metrics)
            )

    def _get_split_resource_metrics_pb2(
        self,
        split_resource_metrics: List[Dict],
    ) -> List[pb2.ResourceMetrics]:
        """Helper that returns a list of pb2.ResourceMetrics objects based on split_resource_metrics.
        Example input:

        ```python
        [
            {
                "resource": <opentelemetry.proto.resource.v1.resource_pb2.Resource>,
                "schema_url": "http://foo-bar",
                "scope_metrics": [
                    "scope": <opentelemetry.proto.common.v1.InstrumentationScope>,
                    "schema_url": "http://foo-baz",
                    "metrics": [
                        {
                            "name": "apples",
                            "description": "number of apples purchased",
                            "sum": {
                                "aggregation_temporality": 1,
                                "is_monotonic": "false",
                                "data_points": [
                                    {
                                        start_time_unix_nano: 1000
                                        time_unix_nano: 1001
                                        exemplars {
                                            time_unix_nano: 1002
                                            span_id: "foo-span"
                                            trace_id: "foo-trace"
                                            as_int: 5
                                        }
                                        as_int: 5
                                    }
                                ]
                            }
                        },
                    ],
                ],
            },
        ]
        ```

        Args:
            split_resource_metrics: A list of dict representations of ResourceMetrics,
                ScopeMetrics, Metrics, and data points.

        Returns:
            List[pb2.ResourceMetrics]: A list of pb2.ResourceMetrics objects containing
                pb2.ScopeMetrics, pb2.Metrics, and data points
        """
        split_resource_metrics_pb = []
        for resource_metrics in split_resource_metrics:
            new_resource_metrics = pb2.ResourceMetrics(
                    resource=resource_metrics.get("resource"),
                    scope_metrics=[],
                    schema_url=resource_metrics.get("schema_url"),
                )
            for scope_metrics in resource_metrics.get("scope_metrics", []):
                new_scope_metrics = pb2.ScopeMetrics(
                        scope=scope_metrics.get("scope"),
                        metrics=[],
                        schema_url=scope_metrics.get("schema_url"),
                    )

                for metric in scope_metrics.get("metrics", []):
                    new_metric = None
                    data_points = []

                    if "sum" in metric:
                        new_metric = pb2.Metric(
                            name=metric.get("name"),
                            description=metric.get("description"),
                            unit=metric.get("unit"),
                            sum=pb2.Sum(
                                data_points=[],
                                aggregation_temporality=metric.get("sum").get("aggregation_temporality"),
                                is_monotonic=metric.get("sum").get("is_monotonic"),
                            )
                        )
                        data_points = metric.get("sum").get("data_points")
                    elif "histogram" in metric:
                        new_metric = pb2.Metric(
                            name=metric.get("name"),
                            description=metric.get("description"),
                            unit=metric.get("unit"),
                            histogram=pb2.Histogram(
                                data_points=[],
                                aggregation_temporality=metric.get("histogram").get("aggregation_temporality"),
                            ),
                        )
                        data_points = metric.get("histogram").get("data_points")
                    elif "exponential_histogram" in metric:
                        new_metric = pb2.Metric(
                            name=metric.get("name"),
                            description=metric.get("description"),
                            unit=metric.get("unit"),
                            exponential_histogram=pb2.ExponentialHistogram(
                                data_points=[],
                                aggregation_temporality=metric.get("exponential_histogram").get("aggregation_temporality"),
                            ),
                        )
                        data_points = metric.get("exponential_histogram").get("data_points")
                    elif "gauge" in metric:
                        new_metric = pb2.Metric(
                            name=metric.get("name"),
                            description=metric.get("description"),
                            unit=metric.get("unit"),
                            gauge=pb2.Gauge(
                                data_points=[],
                            )
                        )
                        data_points = metric.get("gauge").get("data_points")
                    elif "summary" in metric:
                        new_metric = pb2.Metric(
                            name=metric.get("name"),
                            description=metric.get("description"),
                            unit=metric.get("unit"),
                            summary=pb2.Summary(
                                data_points=[],
                            )
                        )
                        data_points = metric.get("summary").get("data_points")
                    else:
                        _logger.warning("Tried to split and export an unsupported metric type. Skipping.")
                        continue

                    for data_point in data_points:
                        if "sum" in metric:
                            new_metric.sum.data_points.append(data_point)
                        elif "histogram" in metric:
                            new_metric.histogram.data_points.append(data_point)
                        elif "exponential_histogram" in metric:
                            new_metric.exponential_histogram.data_points.append(data_point)
                        elif "gauge" in metric:
                            new_metric.gauge.data_points.append(data_point)
                        elif "summary" in metric:
                            new_metric.summary.data_points.append(data_point)
                    
                    new_scope_metrics.metrics.append(new_metric)
                new_resource_metrics.scope_metrics.append(new_scope_metrics)
            split_resource_metrics_pb.append(new_resource_metrics)        
        return split_resource_metrics_pb

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        pass

    @property
    def _exporting(self) -> str:
        return "metrics"

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing."""
        return True


@deprecated(
    version="1.18.0",
    reason="Use one of the encoders from opentelemetry-exporter-otlp-proto-common instead",
)
def get_resource_data(
    sdk_resource_scope_data: Dict[SDKResource, Any],  # ResourceDataT?
    resource_class: Callable[..., PB2Resource],
    name: str,
) -> List[PB2Resource]:
    return _get_resource_data(sdk_resource_scope_data, resource_class, name)


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
