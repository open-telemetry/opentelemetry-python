# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pyright: reportCallIssue=false

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

from opentelemetry.proto_json.common.v1.common import AnyValue as JSONAnyValue
from opentelemetry.proto_json.common.v1.common import (
    ArrayValue as JSONArrayValue,
)
from opentelemetry.proto_json.common.v1.common import (
    InstrumentationScope as JSONInstrumentationScope,
)
from opentelemetry.proto_json.common.v1.common import KeyValue as JSONKeyValue
from opentelemetry.proto_json.common.v1.common import (
    KeyValueList as JSONKeyValueList,
)
from opentelemetry.proto_json.resource.v1.resource import (
    Resource as JSONResource,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.util.types import _ExtendedAttributes

_logger = logging.getLogger(__name__)


def _encode_instrumentation_scope(
    instrumentation_scope: InstrumentationScope | None,
) -> JSONInstrumentationScope:
    return (
        JSONInstrumentationScope(
            name=instrumentation_scope.name,
            version=instrumentation_scope.version,
            attributes=_encode_attributes(instrumentation_scope.attributes),
        )
        if instrumentation_scope is not None
        else JSONInstrumentationScope()
    )


def _encode_resource(resource: Resource) -> JSONResource:
    return JSONResource(attributes=_encode_attributes(resource.attributes))


# pylint: disable-next=too-many-return-statements
def _encode_value(value: Any) -> JSONAnyValue:
    if value is None:
        return JSONAnyValue()
    if isinstance(value, bool):
        return JSONAnyValue(bool_value=value)
    if isinstance(value, str):
        return JSONAnyValue(string_value=value)
    if isinstance(value, int):
        return JSONAnyValue(int_value=value)
    if isinstance(value, float):
        return JSONAnyValue(double_value=value)
    if isinstance(value, bytes):
        return JSONAnyValue(bytes_value=value)
    if isinstance(value, Sequence):
        return JSONAnyValue(
            array_value=JSONArrayValue(
                values=[_encode_value(v) for v in value]
            )
        )
    if isinstance(value, Mapping):
        return JSONAnyValue(
            kvlist_value=JSONKeyValueList(
                values=[_encode_key_value(str(k), v) for k, v in value.items()]
            )
        )
    raise TypeError(f"Invalid type {type(value)} of value {value}")


def _encode_key_value(key: str, value: Any) -> JSONKeyValue:
    return JSONKeyValue(key=key, value=_encode_value(value))


def _encode_span_id(span_id: int) -> bytes:
    return span_id.to_bytes(length=8, byteorder="big", signed=False)


def _encode_trace_id(trace_id: int) -> bytes:
    return trace_id.to_bytes(length=16, byteorder="big", signed=False)


def _encode_attributes(
    attributes: _ExtendedAttributes | None,
) -> list[JSONKeyValue]:
    if not attributes:
        return []
    json_attributes = []
    for key, value in attributes.items():
        # pylint: disable=broad-exception-caught
        try:
            json_attributes.append(_encode_key_value(key, value))
        except Exception as error:
            _logger.exception("Failed to encode key %s: %s", key, error)
    return json_attributes
