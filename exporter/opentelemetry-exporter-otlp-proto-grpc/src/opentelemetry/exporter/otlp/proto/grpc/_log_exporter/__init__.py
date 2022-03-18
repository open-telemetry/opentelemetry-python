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
    get_resource_data,
    _translate_value,
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
)
from opentelemetry.proto.logs.v1.logs_pb2 import LogRecord as PB2LogRecord
from opentelemetry.sdk._logs import LogRecord as SDKLogRecord
from opentelemetry.sdk._logs import LogData
from opentelemetry.sdk._logs.export import LogExporter, LogExportResult


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

    def _translate_name(self, log_data: LogData) -> None:
        self._collector_kwargs["name"] = log_data.log_record.name

    def _translate_time(self, log_data: LogData) -> None:
        self._collector_kwargs[
            "time_unix_nano"
        ] = log_data.log_record.timestamp

    def _translate_span_id(self, log_data: LogData) -> None:
        self._collector_kwargs[
            "span_id"
        ] = log_data.log_record.span_id.to_bytes(8, "big")

    def _translate_trace_id(self, log_data: LogData) -> None:
        self._collector_kwargs[
            "trace_id"
        ] = log_data.log_record.trace_id.to_bytes(16, "big")

    def _translate_trace_flags(self, log_data: LogData) -> None:
        self._collector_kwargs["flags"] = int(log_data.log_record.trace_flags)

    def _translate_body(self, log_data: LogData):
        self._collector_kwargs["body"] = _translate_value(
            log_data.log_record.body
        )

    def _translate_severity_text(self, log_data: LogData):
        self._collector_kwargs[
            "severity_text"
        ] = log_data.log_record.severity_text

    def _translate_data(
        self, data: Sequence[LogData]
    ) -> ExportLogsServiceRequest:
        # pylint: disable=attribute-defined-outside-init

        sdk_resource_instrumentation_library_logs = {}

        for log_data in data:
            resource = log_data.log_record.resource

            instrumentation_library_logs_map = (
                sdk_resource_instrumentation_library_logs.get(resource, {})
            )
            if not instrumentation_library_logs_map:
                sdk_resource_instrumentation_library_logs[
                    resource
                ] = instrumentation_library_logs_map

            instrumentation_library_logs = (
                instrumentation_library_logs_map.get(
                    log_data.instrumentation_info
                )
            )
            if not instrumentation_library_logs:
                if log_data.instrumentation_info is not None:
                    instrumentation_library_logs_map[
                        log_data.instrumentation_info
                    ] = InstrumentationLibraryLogs(
                        instrumentation_library=InstrumentationLibrary(
                            name=log_data.instrumentation_info.name,
                            version=log_data.instrumentation_info.version,
                        )
                    )
                else:
                    instrumentation_library_logs_map[
                        log_data.instrumentation_info
                    ] = InstrumentationLibraryLogs()

            instrumentation_library_logs = (
                instrumentation_library_logs_map.get(
                    log_data.instrumentation_info
                )
            )

            self._collector_kwargs = {}

            self._translate_name(log_data)
            self._translate_time(log_data)
            self._translate_span_id(log_data)
            self._translate_trace_id(log_data)
            self._translate_trace_flags(log_data)
            self._translate_body(log_data)
            self._translate_severity_text(log_data)
            self._collector_kwargs["attributes"] = self._translate_attributes(
                log_data.log_record.attributes
            )

            self._collector_kwargs[
                "severity_number"
            ] = log_data.log_record.severity_number.value

            instrumentation_library_logs.log_records.append(
                PB2LogRecord(**self._collector_kwargs)
            )

        return ExportLogsServiceRequest(
            resource_logs=get_resource_data(
                sdk_resource_instrumentation_library_logs,
                ResourceLogs,
                "logs",
            )
        )

    def export(self, batch: Sequence[LogData]) -> LogExportResult:
        return self._export(batch)

    def shutdown(self) -> None:
        pass
