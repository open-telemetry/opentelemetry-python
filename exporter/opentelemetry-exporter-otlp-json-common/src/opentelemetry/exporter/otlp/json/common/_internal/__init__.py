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

import logging
from collections.abc import Mapping, Sequence
from typing import (
    Any,
    Callable,
    Optional,
    TypeVar,
)

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

_TypingResourceT = TypeVar("_TypingResourceT")
_ResourceDataT = TypeVar("_ResourceDataT")


def _encode_instrumentation_scope(
    instrumentation_scope: InstrumentationScope,
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
def _encode_value(
    value: Any, allow_null: bool = False
) -> Optional[JSONAnyValue]:
    if allow_null is True and value is None:
        return None
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
                values=_encode_array(value, allow_null=allow_null)
            )
        )
    if isinstance(value, Mapping):
        return JSONAnyValue(
            kvlist_value=JSONKeyValueList(
                values=[
                    _encode_key_value(str(k), v, allow_null=allow_null)
                    for k, v in value.items()
                ]
            )
        )
    raise TypeError(f"Invalid type {type(value)} of value {value}")


def _encode_key_value(
    key: str, value: Any, allow_null: bool = False
) -> JSONKeyValue:
    return JSONKeyValue(
        key=key, value=_encode_value(value, allow_null=allow_null)
    )


def _encode_array(
    array: Sequence[Any], allow_null: bool = False
) -> list[JSONAnyValue]:
    if not allow_null:
        # Let the exception get raised by _encode_value()
        return [_encode_value(v, allow_null=allow_null) for v in array]

    return [
        _encode_value(v, allow_null=allow_null)
        if v is not None
        # Use an empty AnyValue to represent None in an array. Behavior may change pending
        # https://github.com/open-telemetry/opentelemetry-specification/issues/4392
        else JSONAnyValue()
        for v in array
    ]


def _encode_span_id(span_id: int) -> bytes:
    return span_id.to_bytes(length=8, byteorder="big", signed=False)


def _encode_trace_id(trace_id: int) -> bytes:
    return trace_id.to_bytes(length=16, byteorder="big", signed=False)


def _encode_attributes(
    attributes: _ExtendedAttributes,
    allow_null: bool = False,
) -> Optional[list[JSONKeyValue]]:
    if not attributes:
        return None
    json_attributes = []
    for key, value in attributes.items():
        # pylint: disable=broad-exception-caught
        try:
            json_attributes.append(
                _encode_key_value(key, value, allow_null=allow_null)
            )
        except Exception as error:
            _logger.exception("Failed to encode key %s: %s", key, error)
    return json_attributes


def _get_resource_data(
    sdk_resource_scope_data: dict[Resource, _ResourceDataT],
    resource_class: Callable[..., _TypingResourceT],
    name: str,
) -> list[_TypingResourceT]:
    resource_data = []

    for (
        sdk_resource,
        scope_data,
    ) in sdk_resource_scope_data.items():
        json_resource = JSONResource(
            attributes=_encode_attributes(sdk_resource.attributes)
        )
        resource_data.append(
            resource_class(
                **{
                    "resource": json_resource,
                    f"scope_{name}": scope_data.values(),
                }
            )
        )
    return resource_data
