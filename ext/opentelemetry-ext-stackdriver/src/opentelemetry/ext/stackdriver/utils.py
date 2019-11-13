# Copyright 2018, OpenCensus Authors
# Copyright 2019, OpenTelemetry Authors
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
import datetime
import logging

import opentelemetry.trace as trace_api
from opentelemetry.sdk.util import ns_to_iso_str
from opentelemetry.util import types

# Max length is 128 bytes for a truncatable string.
MAX_LENGTH = 128


def get_truncatable_str(str_to_convert):
    """Truncate a string if exceed limit and record the truncated bytes
        count.
    """
    truncated, truncated_byte_count = check_str_length(
        str_to_convert, MAX_LENGTH
    )

    result = {
        "value": truncated,
        "truncated_byte_count": truncated_byte_count,
    }
    return result


def check_str_length(str_to_check, limit=MAX_LENGTH):
    """Check the length of a string. If exceeds limit, then truncate it.
    """
    str_bytes = str_to_check.encode("utf-8")
    str_len = len(str_bytes)
    truncated_byte_count = 0

    if str_len > limit:
        truncated_byte_count = str_len - limit
        str_bytes = str_bytes[:limit]

    result = str(str_bytes.decode("utf-8", errors="ignore"))

    return (result, truncated_byte_count)


def extract_status(status: trace_api.Status):
    """Convert a Status object to dict."""
    status_json = {"details": None}

    status_json["code"] = status.canonical_code.value

    if status.description is not None:
        status_json["message"] = status.description

    return status_json


def extract_links(links):
    """Convert span.links to set."""
    if not links:
        return None

    links = []
    for link in links:
        trace_id = link.context.trace_id
        span_id = link.context.span_id
        links.append(
            {trace_id: trace_id, span_id: span_id, type: "CHILD_LINKED_SPAN"}
        )
    return set(links)


def extract_events(events):
    """Convert span.events to dict."""
    if not events:
        return None

    logs = []

    for event in events:
        annotation_json = {"description": get_truncatable_str(event.name)}
        if event.attributes is not None:
            annotation_json["attributes"] = extract_attributes(
                event.attributes
            )

        logs.append(
            {
                "time": ns_to_iso_str(event.timestamp),
                "annotation": annotation_json,
            }
        )
    return logs


def extract_attributes(attrs: types.Attributes):
    """Convert span.attributes to dict."""
    attributes_json = {}

    for key, value in attrs.items():
        key = check_str_length(key)[0]
        value = _format_attribute_value(value)

        if value is not None:
            attributes_json[key] = value

    result = {"attributeMap": attributes_json}

    return result


def map_attributes(attribute_map):
    """Convert the attributes to stackdriver attributes."""
    if attribute_map is None:
        return attribute_map
    for (key, value) in attribute_map.items():
        if key != "attributeMap":
            continue
        for attribute_key in list(value.keys()):
            if attribute_key in ATTRIBUTE_MAPPING:
                new_key = ATTRIBUTE_MAPPING.get(attribute_key)
                value[new_key] = value.pop(attribute_key)
    return attribute_map


def _format_attribute_value(value):
    if isinstance(value, bool):
        value_type = "bool_value"
    elif isinstance(value, int):
        value_type = "int_value"
    elif isinstance(value, str):
        value_type = "string_value"
        value = get_truncatable_str(value)
    elif isinstance(value, float):
        value_type = "double_value"
    else:
        return None

    return {value_type: value}


ATTRIBUTE_MAPPING = {
    "component": "/component",
    "error.message": "/error/message",
    "error.name": "/error/name",
    "http.client_city": "/http/client_city",
    "http.client_country": "/http/client_country",
    "http.client_protocol": "/http/client_protocol",
    "http.client_region": "/http/client_region",
    "http.host": "/http/host",
    "http.method": "/http/method",
    "http.redirected_url": "/http/redirected_url",
    "http.request_size": "/http/request/size",
    "http.response_size": "/http/response/size",
    "http.status_code": "/http/status_code",
    "http.url": "/http/url",
    "http.user_agent": "/http/user_agent",
    "pid": "/pid",
    "stacktrace": "/stacktrace",
    "tid": "/tid",
    "grpc.host_port": "/grpc/host_port",
    "grpc.method": "/grpc/method",
}
