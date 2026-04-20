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

from __future__ import annotations

from collections import defaultdict
from collections.abc import Collection
from typing import cast

from opentelemetry.exporter.otlp.json.common._internal import (
    _encode_attributes,
    _encode_instrumentation_scope,
    _encode_resource,
    _encode_span_id,
    _encode_trace_id,
    _encode_value,
)
from opentelemetry.proto_json.collector.logs.v1.logs_service import (
    ExportLogsServiceRequest as JSONExportLogsServiceRequest,
)
from opentelemetry.proto_json.logs.v1.logs import LogRecord as JSONLogRecord
from opentelemetry.proto_json.logs.v1.logs import (
    ResourceLogs as JSONResourceLogs,
)
from opentelemetry.proto_json.logs.v1.logs import (
    ScopeLogs as JSONScopeLogs,
)
from opentelemetry.sdk._logs import ReadableLogRecord
from opentelemetry.util.types import Attributes


def encode_logs(
    batch: Collection[ReadableLogRecord],
) -> JSONExportLogsServiceRequest:
    return JSONExportLogsServiceRequest(
        resource_logs=_encode_resource_logs(batch)
    )


def _encode_log(readable_log_record: ReadableLogRecord) -> JSONLogRecord:
    return JSONLogRecord(
        time_unix_nano=readable_log_record.log_record.timestamp,
        observed_time_unix_nano=readable_log_record.log_record.observed_timestamp,
        span_id=_encode_span_id(readable_log_record.log_record.span_id)
        if readable_log_record.log_record.span_id
        else None,
        trace_id=_encode_trace_id(readable_log_record.log_record.trace_id)
        if readable_log_record.log_record.trace_id
        else None,
        flags=int(readable_log_record.log_record.trace_flags),
        body=_encode_value(
            readable_log_record.log_record.body, allow_null=True
        ),
        severity_text=readable_log_record.log_record.severity_text,
        attributes=_encode_attributes(
            cast(Attributes, readable_log_record.log_record.attributes),
            allow_null=True,
        ),
        dropped_attributes_count=readable_log_record.dropped_attributes,
        severity_number=getattr(
            readable_log_record.log_record.severity_number, "value", None
        ),
        event_name=readable_log_record.log_record.event_name,
    )


def _encode_resource_logs(
    batch: Collection[ReadableLogRecord],
) -> list[JSONResourceLogs]:
    sdk_resource_logs = defaultdict(lambda: defaultdict(list))

    for readable_log in batch:
        sdk_resource = readable_log.resource
        sdk_instrumentation = readable_log.instrumentation_scope or None
        sdk_resource_logs[sdk_resource][sdk_instrumentation].append(
            _encode_log(readable_log)
        )

    json_resource_logs = []
    for sdk_resource, sdk_instrumentations in sdk_resource_logs.items():
        scope_logs = []
        for sdk_instrumentation, json_logs in sdk_instrumentations.items():
            scope_logs.append(
                JSONScopeLogs(
                    scope=(_encode_instrumentation_scope(sdk_instrumentation)),
                    log_records=json_logs,
                    schema_url=sdk_instrumentation.schema_url
                    if sdk_instrumentation
                    else None,
                )
            )
        json_resource_logs.append(
            JSONResourceLogs(
                resource=_encode_resource(sdk_resource),
                scope_logs=scope_logs,
                schema_url=sdk_resource.schema_url,
            )
        )

    return json_resource_logs
