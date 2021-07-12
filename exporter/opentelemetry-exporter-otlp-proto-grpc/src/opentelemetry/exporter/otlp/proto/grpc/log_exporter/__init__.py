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

from typing import Optional, Sequence
from grpc import ChannelCredentials, Compression
from opentelemetry.exporter.otlp.proto.grpc.exporter import (
    OTLPExporterMixin,
    _translate_key_values,
    get_resource_data,
)
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
)
from opentelemetry.proto.collector.logs.v1.logs_service_pb2_grpc import (
    LogsServiceStub,
)
from opentelemetry.proto.common.v1.common_pb2 import InstrumentationLibrary
from opentelemetry.proto.logs.v1.logs_pb2 import (
    InstrumentationLibraryLogs,
    ResourceLogs,
    SeverityNumber,
)
from opentelemetry.proto.logs.v1.logs_pb2 import LogRecord as PB2LogRecord
from opentelemetry.sdk.logs import LogRecord as SDKLogRecord
from opentelemetry.sdk.logs import LogExporter, LogExportResult


class OTLPLogExporter(
    LogExporter,
    OTLPExporterMixin[SDKLogRecord, ExportLogsServiceRequest, LogExportResult],
):

    _result = LogExportResult
    _stub = LogsServiceStub

    def __init__(
        self,
        endpoint: Optional[str] = None,
        insecure: Optional[bool] = None,
        credentials: Optional[ChannelCredentials] = None,
        headers: Optional[Sequence] = None,
        timeout: Optional[int] = None,
        compression: Optional[Compression] = None,
    ):
        endpoint = "localhost:4317"
        insecure = True
        timeout = 10
        compression = None

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

    def _translate_name(self, log_data) -> None:
        self._collector_log_kwargs["name"] = log_data.record.name

    def _translate_time(self, log_data) -> None:
        self._collector_log_kwargs["time_unix_nano"] = log_data.timestamp

    def _translate_span_id(self, log_data) -> None:
        self._collector_log_kwargs[
            "span_id"
        ] = log_data.record.span_id.to_bytes(8, "big")

    def _translate_trace_id(self, log_data) -> None:
        self._collector_log_kwargs[
            "trace_id"
        ] = log_data.record.trace_id.to_bytes(16, "big")

    def _translate_body(self, log_data):
        self._collector_log_kwargs["body"] = log_data.record.body

    def _translate_severity_text(self, log_data):
        self._collector_log_kwargs[
            "severity_text"
        ] = log_data.record.severity_text

    def _translate_attributes(self, log_data) -> None:
        if log_data.record.attributes:

            self._collector_log_kwargs["attributes"] = []

            for key, value in log_data.record.attributes.items():

                try:
                    self._collector_log_kwargs["attributes"].append(
                        _translate_key_values(key, value)
                    )
                except Exception as error:  # pylint: disable=broad-except
                    pass

    def _translate_data(
        self, data: Sequence[SDKLogRecord]
    ) -> ExportLogsServiceRequest:
        # pylint: disable=attribute-defined-outside-init

        sdk_resource_instrumentation_library_logs = {}

        for log_data in data:

            if log_data.record.resource not in (
                sdk_resource_instrumentation_library_logs.keys()
            ):
                if log_data.instrumentation_info is not None:
                    instrumentation_library_logs = InstrumentationLibraryLogs(
                        instrumentation_library=InstrumentationLibrary(
                            name=log_data.instrumentation_info.name,
                            version=log_data.instrumentation_info.version,
                        )
                    )

                else:
                    instrumentation_library_logs = InstrumentationLibraryLogs()

                sdk_resource_instrumentation_library_logs[
                    log_data.resource
                ] = instrumentation_library_logs

            self._collector_log_kwargs = {}

            self._translate_name(log_data)
            self._translate_time(log_data)
            self._translate_span_id(log_data)
            self._translate_trace_id(log_data)
            self._translate_attributes(log_data)

            self._collector_log_kwargs["severity_number"] = getattr(
                SeverityNumber,
                "SEVERITY_NUMBER_{}".format(log_data.resource.severity_text),
            )

            sdk_resource_instrumentation_library_logs[
                log_data.resource
            ].logs.append(PB2LogRecord(**self._collector_log_kwargs))

        return ExportLogsServiceRequest(
            resource_logs=get_resource_data(
                sdk_resource_instrumentation_library_logs,
                ResourceLogs,
                "logs",
            )
        )

    def export(self, logs: Sequence[SDKLogRecord]) -> LogExportResult:
        return self._export(logs)
