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
    _get_credentials,
    _translate_value,
    environ_to_compression,
)
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
)
from opentelemetry.proto.collector.logs.v1.logs_service_pb2_grpc import (
    LogsServiceStub,
)
from opentelemetry.proto.common.v1.common_pb2 import InstrumentationScope
from opentelemetry.proto.logs.v1.logs_pb2 import (
    ScopeLogs,
    ResourceLogs,
)
from opentelemetry.proto.logs.v1.logs_pb2 import LogRecord as PB2LogRecord
from opentelemetry.sdk._logs import LogRecord as SDKLogRecord
from opentelemetry.sdk._logs import LogData
from opentelemetry.sdk._logs.export import LogExporter, LogExportResult

from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_COMPRESSION,
    OTEL_EXPORTER_OTLP_LOGS_ENDPOINT,
    OTEL_EXPORTER_OTLP_LOGS_HEADERS,
    OTEL_EXPORTER_OTLP_LOGS_INSECURE,
    OTEL_EXPORTER_OTLP_LOGS_TIMEOUT,
)


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
        if insecure is None:
            insecure = environ.get(OTEL_EXPORTER_OTLP_LOGS_INSECURE)
            if insecure is not None:
                insecure = insecure.lower() == "true"

        if (
            not insecure
            and environ.get(OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE) is not None
        ):
            credentials = _get_credentials(
                credentials, OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE
            )

        environ_timeout = environ.get(OTEL_EXPORTER_OTLP_LOGS_TIMEOUT)
        environ_timeout = (
            int(environ_timeout) if environ_timeout is not None else None
        )

        compression = (
            environ_to_compression(OTEL_EXPORTER_OTLP_LOGS_COMPRESSION)
            if compression is None
            else compression
        )
        endpoint = endpoint or environ.get(OTEL_EXPORTER_OTLP_LOGS_ENDPOINT)

        headers = headers or environ.get(OTEL_EXPORTER_OTLP_LOGS_HEADERS)

        super().__init__(
            **{
                "endpoint": endpoint,
                "insecure": insecure,
                "credentials": credentials,
                "headers": headers,
                "timeout": timeout or environ_timeout,
                "compression": compression,
            }
        )

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

        sdk_resource_scope_logs = {}

        for log_data in data:
            resource = log_data.log_record.resource

            scope_logs_map = sdk_resource_scope_logs.get(resource, {})
            if not scope_logs_map:
                sdk_resource_scope_logs[resource] = scope_logs_map

            scope_logs = scope_logs_map.get(log_data.instrumentation_scope)
            if not scope_logs:
                if log_data.instrumentation_scope is not None:
                    scope_logs_map[log_data.instrumentation_scope] = ScopeLogs(
                        scope=InstrumentationScope(
                            name=log_data.instrumentation_scope.name,
                            version=log_data.instrumentation_scope.version,
                        )
                    )
                else:
                    scope_logs_map[
                        log_data.instrumentation_scope
                    ] = ScopeLogs()

            scope_logs = scope_logs_map.get(log_data.instrumentation_scope)

            self._collector_kwargs = {}

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

            scope_logs.log_records.append(
                PB2LogRecord(**self._collector_kwargs)
            )

        return ExportLogsServiceRequest(
            resource_logs=get_resource_data(
                sdk_resource_scope_logs,
                ResourceLogs,
                "logs",
            )
        )

    def export(self, batch: Sequence[LogData]) -> LogExportResult:
        return self._export(batch)

    def shutdown(self) -> None:
        pass

    @property
    def _exporting(self) -> str:
        return "logs"
