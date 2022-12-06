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

from os import environ
from typing import Dict, Optional

from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http.exporter import (
    _OTLPExporterMixin,
    DEFAULT_ENDPOINT,
    DEFAULT_TIMEOUT,
    _compression_from_env,
)
from opentelemetry.sdk.metrics._internal.aggregation import Aggregation

from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_TIMEOUT,
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
    MetricExporter,
    MetricExportResult,
    MetricsData,
    ResourceMetrics,
)
from opentelemetry.util.re import parse_env_headers
from opentelemetry.exporter.otlp.proto.http.metric_exporter.encoder import (
    _ProtobufEncoder,
)
import requests


DEFAULT_METRICS_EXPORT_PATH = "v1/metrics"


class OTLPMetricExporter(
    MetricExporter, _OTLPExporterMixin[ResourceMetrics, MetricExportResult]
):

    _MAX_RETRY_TIMEOUT = 64
    _encoder = _ProtobufEncoder
    _result = MetricExportResult

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
        self._compression = compression or _compression_from_env(
            OTEL_EXPORTER_OTLP_METRICS_COMPRESSION
        )
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

        _OTLPExporterMixin.__init__(
            self,
            self._endpoint,
            self._certificate_file,
            self._headers,
            self._timeout,
            self._compression,
            self._session,
        )

        MetricExporter.__init__(
            self,
            preferred_temporality=instrument_class_temporality,
            preferred_aggregation=preferred_aggregation,
        )

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        return _OTLPExporterMixin.export(self, metrics_data)

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        pass

    @property
    def _exporting(self) -> str:
        return "metrics"

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return True


def _append_metrics_path(endpoint: str) -> str:
    if endpoint.endswith("/"):
        return endpoint + DEFAULT_METRICS_EXPORT_PATH
    return endpoint + f"/{DEFAULT_METRICS_EXPORT_PATH}"
