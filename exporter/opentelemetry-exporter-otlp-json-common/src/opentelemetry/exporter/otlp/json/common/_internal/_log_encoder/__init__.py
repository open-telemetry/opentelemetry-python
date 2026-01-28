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

"""JSON encoder for OpenTelemetry logs to match the ProtoJSON format."""

import base64
from typing import Any, Dict, List, Optional, Sequence

from opentelemetry._logs import SeverityNumber
from opentelemetry.sdk._logs import ReadableLogRecord
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.exporter.otlp.json.common._internal.encoder_utils import encode_id
from opentelemetry.exporter.otlp.json.common.encoding import IdEncoding

def encode_logs(
        batch: Sequence[ReadableLogRecord],
        id_encoding: Optional[IdEncoding] = None) -> Dict[str, Any]:
    """Encodes logs in the OTLP JSON format.

    Returns:
        A dict representing the logs in OTLP JSON format as specified in the
        OpenTelemetry Protocol and ProtoJSON format.
    """
    id_encoding = id_encoding or IdEncoding.BASE64

    # Group logs by resource
    resource_logs = {}
    for readable_log_record in batch:
        resource_key = _compute_resource_hashcode(readable_log_record.resource)

        if resource_key not in resource_logs:
            resource_logs[resource_key] = {
                "resource": _encode_resource(readable_log_record.resource),
                "scopeLogs": {},
                "schemaUrl": getattr(
                    readable_log_record.resource, "schema_url", ""
                ),
            }

        # Group logs by instrumentation scope within each resource
        scope_key = _compute_instrumentation_scope_hashcode(
            readable_log_record.instrumentation_scope
        )
        scope_logs = resource_logs[resource_key]["scopeLogs"]

        if scope_key not in scope_logs:
            scope_logs[scope_key] = {
                "scope": _encode_instrumentation_scope(
                    readable_log_record.instrumentation_scope
                ),
                "logRecords": [],
                "schemaUrl": (
                    getattr(readable_log_record.instrumentation_scope, "schema_url", "")
                    if readable_log_record.instrumentation_scope
                    else ""
                ),
            }

        # Add log record to the appropriate scope
        scope_logs[scope_key]["logRecords"].append(
            _encode_log_record(readable_log_record, id_encoding)
        )

    # Convert dictionaries to lists for JSON output
    resource_logs_list = []
    for resource_readable_log_record in resource_logs.values():
        scope_logs_list = []
        for scope_readable_log_record in resource_readable_log_record["scopeLogs"].values():
            scope_logs_list.append(scope_readable_log_record)

        resource_readable_log_record["scopeLogs"] = scope_logs_list
        resource_logs_list.append(resource_readable_log_record)

    return {"resourceLogs": resource_logs_list}


def _compute_resource_hashcode(resource: Resource) -> str:
    """Computes a hashcode for the resource based on its attributes."""
    if not resource or not resource.attributes:
        return ""
    # Simple implementation: use string representation of sorted attributes
    return str(sorted(resource.attributes.items()))


def _compute_instrumentation_scope_hashcode(
    scope: Optional[InstrumentationScope],
) -> str:
    """Computes a hashcode for the instrumentation scope."""
    if scope is None:
        return ""
    return f"{scope.name}|{scope.version}"


def _encode_resource(resource: Resource) -> Dict[str, Any]:
    """Encodes a resource into OTLP JSON format."""
    if not resource:
        return {"attributes": []}

    return {
        "attributes": _encode_attributes(resource.attributes),
        "droppedAttributesCount": 0,  # Not tracking dropped attributes yet
    }


def _encode_instrumentation_scope(
    scope: Optional[InstrumentationScope],
) -> Dict[str, Any]:
    """Encodes an instrumentation scope into OTLP JSON format."""
    if scope is None:
        return {"name": "", "version": ""}

    return {
        "name": scope.name or "",
        "version": scope.version or "",
        "attributes": [],  # Not using attributes for scope yet
        "droppedAttributesCount": 0,
    }


def _encode_log_record(
        readable_log_record: ReadableLogRecord,
        id_encoding: IdEncoding) -> Dict[str, Any]:
    """Encodes a log record into OTLP JSON format."""
    log_record = readable_log_record.log_record

    result = {
        "timeUnixNano": str(log_record.timestamp),
        "observedTimeUnixNano": str(
            getattr(log_record, "observed_timestamp", log_record.timestamp)
        ),
        "severityNumber": _get_severity_number_value(
            log_record.severity_number
        ),
        "severityText": log_record.severity_text or "",
        "attributes": _encode_attributes(log_record.attributes),
        "droppedAttributesCount": (
            readable_log_record.dropped_attributes
            if hasattr(readable_log_record, "dropped_attributes")
            else 0
        ),
    }

    # Handle body based on type
    if log_record.body is not None:
        result.update(_encode_any_value(log_record.body))

    # Handle trace context if present
    if log_record.trace_id:
        result["traceId"] = encode_id(id_encoding, log_record.trace_id, 16)

    if log_record.span_id:
        result["spanId"] = encode_id(id_encoding, log_record.span_id, 8)

    if (
        hasattr(log_record, "trace_flags")
        and log_record.trace_flags is not None
    ):
        result["flags"] = int(log_record.trace_flags)

    return result


def _encode_attributes(attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Encodes attributes into OTLP JSON format."""
    if not attributes:
        return []

    attribute_list = []
    for key, value in attributes.items():
        if value is None:
            continue

        attribute = {"key": key}
        attribute.update(_encode_attribute_value(value))
        attribute_list.append(attribute)

    return attribute_list


# pylint: disable=too-many-return-statements
def _encode_attribute_value(value: Any) -> Dict[str, Any]:
    """Encodes a single attribute value into OTLP JSON format."""
    if isinstance(value, bool):
        return {"value": {"boolValue": value}}
    if isinstance(value, int):
        return {"value": {"intValue": str(value)}}
    if isinstance(value, float):
        return {"value": {"doubleValue": value}}
    if isinstance(value, str):
        return {"value": {"stringValue": value}}
    if isinstance(value, (list, tuple)):
        if not value:
            return {"value": {"arrayValue": {"values": []}}}

        array_value = {"values": []}
        for element in value:
            element_value = _encode_attribute_value(element)["value"]
            array_value["values"].append(element_value)

        return {"value": {"arrayValue": array_value}}
    if isinstance(value, bytes):
        return {
            "value": {"bytesValue": base64.b64encode(value).decode("ascii")}
        }
    # Convert anything else to string
    return {"value": {"stringValue": str(value)}}


# pylint: disable=too-many-return-statements
def _encode_any_value(value: Any) -> Dict[str, Any]:
    """Encodes any log record body value into OTLP JSON format."""
    if isinstance(value, bool):
        return {"boolValue": value}
    if isinstance(value, int):
        return {"intValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    if isinstance(value, str):
        return {"stringValue": value}
    if isinstance(value, (list, tuple)):
        values = []
        for element in value:
            values.append(_encode_any_value(element))
        return {"arrayValue": {"values": values}}
    if isinstance(value, dict):
        kvlist = []
        for key, val in value.items():
            if val is not None:
                kv = {"key": str(key)}
                kv.update(_encode_any_value(val))
                kvlist.append(kv)
        return {"kvlistValue": {"values": kvlist}}
    if isinstance(value, bytes):
        return {"bytesValue": base64.b64encode(value).decode("ascii")}
    # Convert anything else to string
    return {"stringValue": str(value)}


def _get_severity_number_value(severity_number: SeverityNumber) -> str:
    """Converts a SeverityNumber enum to its string representation for ProtoJSON format."""
    severity_map = {
        SeverityNumber.UNSPECIFIED: "SEVERITY_NUMBER_UNSPECIFIED",
        SeverityNumber.TRACE: "SEVERITY_NUMBER_TRACE",
        SeverityNumber.TRACE2: "SEVERITY_NUMBER_TRACE2",
        SeverityNumber.TRACE3: "SEVERITY_NUMBER_TRACE3",
        SeverityNumber.TRACE4: "SEVERITY_NUMBER_TRACE4",
        SeverityNumber.DEBUG: "SEVERITY_NUMBER_DEBUG",
        SeverityNumber.DEBUG2: "SEVERITY_NUMBER_DEBUG2",
        SeverityNumber.DEBUG3: "SEVERITY_NUMBER_DEBUG3",
        SeverityNumber.DEBUG4: "SEVERITY_NUMBER_DEBUG4",
        SeverityNumber.INFO: "SEVERITY_NUMBER_INFO",
        SeverityNumber.INFO2: "SEVERITY_NUMBER_INFO2",
        SeverityNumber.INFO3: "SEVERITY_NUMBER_INFO3",
        SeverityNumber.INFO4: "SEVERITY_NUMBER_INFO4",
        SeverityNumber.WARN: "SEVERITY_NUMBER_WARN",
        SeverityNumber.WARN2: "SEVERITY_NUMBER_WARN2",
        SeverityNumber.WARN3: "SEVERITY_NUMBER_WARN3",
        SeverityNumber.WARN4: "SEVERITY_NUMBER_WARN4",
        SeverityNumber.ERROR: "SEVERITY_NUMBER_ERROR",
        SeverityNumber.ERROR2: "SEVERITY_NUMBER_ERROR2",
        SeverityNumber.ERROR3: "SEVERITY_NUMBER_ERROR3",
        SeverityNumber.ERROR4: "SEVERITY_NUMBER_ERROR4",
        SeverityNumber.FATAL: "SEVERITY_NUMBER_FATAL",
        SeverityNumber.FATAL2: "SEVERITY_NUMBER_FATAL2",
        SeverityNumber.FATAL3: "SEVERITY_NUMBER_FATAL3",
        SeverityNumber.FATAL4: "SEVERITY_NUMBER_FATAL4",
    }
    return severity_map.get(severity_number, "SEVERITY_NUMBER_UNSPECIFIED")
