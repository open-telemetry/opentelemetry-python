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
from typing import Optional, Sequence
from grpc import ChannelCredentials, Compression
from opentelemetry.exporter.otlp.proto.grpc.exporter import (
    OTLPExporterMixin,
    get_resource_data,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2_grpc import (
    MetricsServiceStub,
)
from opentelemetry.proto.common.v1.common_pb2 import InstrumentationLibrary
from opentelemetry.proto.metrics.v1.metrics_pb2 import (
    InstrumentationLibraryMetrics,
    ResourceMetrics,
)
from opentelemetry.proto.metrics.v1.metrics_pb2 import Metric as PB2Metric
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_METRICS_INSECURE,
)
from opentelemetry.sdk._metrics.point import (
    Metric,
)

from opentelemetry.sdk._metrics.export import (
    MetricExporter,
    MetricExportResult,
)


class OTLPMetricExporter(
    MetricExporter,
    OTLPExporterMixin[Metric, ExportMetricsServiceRequest, MetricExportResult],
):
    _result = MetricExportResult
    _stub = MetricsServiceStub

    def __init__(
        self,
        endpoint: Optional[str] = None,
        insecure: Optional[bool] = None,
        credentials: Optional[ChannelCredentials] = None,
        headers: Optional[Sequence] = None,
        timeout: Optional[int] = None,
        compression: Optional[Compression] = None,
    ):

        if insecure is None:
            insecure = environ.get(OTEL_EXPORTER_OTLP_METRICS_INSECURE)
            if insecure is not None:
                insecure = insecure.lower() == "true"

        super().__init__(
            **{
                "endpoint": endpoint,
                "insecure": insecure,
                "credentials": credentials,
                "headers": headers,
                "timeout": timeout,
                "compression": compression,
            }
        )

    def _translate_data(
        self, data: Sequence[Metric]
    ) -> ExportMetricsServiceRequest:
        sdk_resource_instrumentation_library_metrics = {}
        self._collector_metric_kwargs = {}

        for metric in data:
            resource = metric.resource
            instrumentation_library_map = (
                sdk_resource_instrumentation_library_metrics.get(resource, {})
            )
            if not instrumentation_library_map:
                sdk_resource_instrumentation_library_metrics[
                    resource
                ] = instrumentation_library_map

            instrumentation_library_metrics = instrumentation_library_map.get(
                metric.instrumentation_info
            )

            if not instrumentation_library_metrics:
                if metric.instrumentation_info is not None:
                    instrumentation_library_map[
                        metric.instrumentation_info
                    ] = InstrumentationLibraryMetrics(
                        instrumentation_library=InstrumentationLibrary(
                            name=metric.instrumentation_info.name,
                            version=metric.instrumentation_info.version,
                        )
                    )
                else:
                    instrumentation_library_map[
                        metric.instrumentation_info
                    ] = InstrumentationLibraryMetrics()

            instrumentation_library_metrics = instrumentation_library_map.get(
                metric.instrumentation_info
            )

            instrumentation_library_metrics.metrics.append(
                PB2Metric(**self._collector_metric_kwargs)
            )
        return ExportMetricsServiceRequest(
            resource_metrics=get_resource_data(
                sdk_resource_instrumentation_library_metrics,
                ResourceMetrics,
                "metrics",
            )
        )

    def export(self, metrics: Sequence[Metric]) -> MetricExportResult:
        return self._export(metrics)

    def shutdown(self):
        pass
