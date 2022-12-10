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

from typing import Sequence, List

from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
)
from opentelemetry.proto.logs.v1.logs_pb2 import (
    ScopeLogs,
    ResourceLogs,
)
from opentelemetry.proto.logs.v1.logs_pb2 import LogRecord as PB2LogRecord
from opentelemetry.exporter.otlp.proto.http.trace_exporter.encoder import (
    _encode_instrumentation_scope,
    _encode_resource,
    _encode_span_id,
    _encode_trace_id,
    _encode_value,
    _encode_attributes,
)


from opentelemetry.sdk._logs import LogData


class _ProtobufEncoder:
    @classmethod
    def serialize(cls, batch: Sequence[LogData]) -> str:
        return cls.encode(batch).SerializeToString()

    @staticmethod
    def encode(batch: Sequence[LogData]) -> ExportLogsServiceRequest:
        return ExportLogsServiceRequest(
            resource_logs=_encode_resource_logs(batch)
        )


def _encode_log(log_data: LogData) -> PB2LogRecord:
    kwargs = {}
    kwargs["time_unix_nano"] = log_data.log_record.timestamp
    kwargs["span_id"] = _encode_span_id(log_data.log_record.span_id)
    kwargs["trace_id"] = _encode_trace_id(log_data.log_record.trace_id)
    kwargs["flags"] = int(log_data.log_record.trace_flags)
    kwargs["body"] = _encode_value(log_data.log_record.body)
    kwargs["severity_text"] = log_data.log_record.severity_text
    kwargs["attributes"] = _encode_attributes(log_data.log_record.attributes)
    kwargs["severity_number"] = log_data.log_record.severity_number.value

    return PB2LogRecord(**kwargs)


def _encode_resource_logs(batch: Sequence[LogData]) -> List[ResourceLogs]:

    sdk_resource_logs = {}

    for sdk_log in batch:
        sdk_resource = sdk_log.log_record.resource
        sdk_instrumentation = sdk_log.instrumentation_scope or None
        pb2_log = _encode_log(sdk_log)

        if sdk_resource not in sdk_resource_logs.keys():
            sdk_resource_logs[sdk_resource] = {sdk_instrumentation: [pb2_log]}
        elif sdk_instrumentation not in sdk_resource_logs[sdk_resource].keys():
            sdk_resource_logs[sdk_resource][sdk_instrumentation] = [pb2_log]
        else:
            sdk_resource_logs[sdk_resource][sdk_instrumentation].append(
                pb2_log
            )

    pb2_resource_logs = []

    for sdk_resource, sdk_instrumentations in sdk_resource_logs.items():
        scope_logs = []
        for sdk_instrumentation, pb2_logs in sdk_instrumentations.items():
            scope_logs.append(
                ScopeLogs(
                    scope=(_encode_instrumentation_scope(sdk_instrumentation)),
                    log_records=pb2_logs,
                )
            )
        pb2_resource_logs.append(
            ResourceLogs(
                resource=_encode_resource(sdk_resource),
                scope_logs=scope_logs,
            )
        )

    return pb2_resource_logs
