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

import base64
import logging
from collections.abc import Sequence
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Mapping,
    Optional,
    TypeVar,
)

from opentelemetry.sdk.trace import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.util.types import Attributes

_logger = logging.getLogger(__name__)

_TypingResourceT = TypeVar("_TypingResourceT")
_ResourceDataT = TypeVar("_ResourceDataT")


def _encode_instrumentation_scope(
    instrumentation_scope: InstrumentationScope,
) -> Dict[str, Any]:
    """
    Encodes an InstrumentationScope object to a JSON-serializable dict.

    Args:
        instrumentation_scope: The instrumentation scope to encode

    Returns:
        A dict representing the instrumentation scope
    """
    if instrumentation_scope is None:
        return {}

    scope_dict = {
        "name": instrumentation_scope.name,
    }

    if instrumentation_scope.version:
        scope_dict["version"] = instrumentation_scope.version

    if instrumentation_scope.attributes:
        scope_dict["attributes"] = _encode_attributes(
            instrumentation_scope.attributes
        )

    return scope_dict


def _encode_resource(resource: Resource) -> Dict[str, Any]:
    """
    Encodes a Resource object to a JSON-serializable dict.

    Args:
        resource: The resource to encode

    Returns:
        A dict representing the resource
    """
    if resource is None or not resource.attributes:
        return {}

    return {"attributes": _encode_attributes(resource.attributes)}


def _encode_value(value: Any, allow_null: bool = False) -> Optional[Any]:
    """
    Encodes a value for use in OTLP JSON format.

    Args:
        value: The value to encode.
        allow_null: Whether to allow null values.

    Returns:
        The encoded value.
    """
    if allow_null is True and value is None:
        return None
    if isinstance(value, (bool, str, int, float)):
        return value
    if isinstance(value, bytes):
        # Convert bytes to base64 string for JSON
        return {"bytes_value": base64.b64encode(value).decode("ascii")}
    if isinstance(value, Sequence):
        return _encode_array(value, allow_null=allow_null)
    if isinstance(value, Mapping):
        return {
            "kvlist_value": {
                str(k): _encode_value(v, allow_null=allow_null)
                for k, v in value.items()
            }
        }

    raise ValueError(f"Invalid type {type(value)} of value {value}")


def _encode_key_value(
    key: str, value: Any, allow_null: bool = False
) -> Dict[str, Any]:
    """
    Encodes a key-value pair to a JSON-serializable dict.

    Args:
        key: The key
        value: The value
        allow_null: Whether null values are allowed

    Returns:
        A dict representing the key-value pair
    """
    return {key: _encode_value(value, allow_null=allow_null)}


def _encode_array(array: Sequence[Any], allow_null: bool = False) -> List[Any]:
    """
    Encodes an array to a JSON-serializable list.

    Args:
        array: The array to encode
        allow_null: Whether null values are allowed

    Returns:
        A list of encoded values
    """
    if not allow_null:
        return [_encode_value(v, allow_null=allow_null) for v in array]

    return [
        _encode_value(v, allow_null=allow_null) if v is not None else None
        for v in array
    ]


def _encode_span_id(span_id: int) -> str:
    """
    Encodes a span ID to a hexadecimal string.

    Args:
        span_id: The span ID as an integer

    Returns:
        The span ID as a 16-character hexadecimal string
    """
    return f"{span_id:016x}"


def _encode_trace_id(trace_id: int) -> str:
    """
    Encodes a trace ID to a hexadecimal string.

    Args:
        trace_id: The trace ID as an integer

    Returns:
        The trace ID as a 32-character hexadecimal string
    """
    return f"{trace_id:032x}"


def _encode_attributes(
    attributes: Attributes,
) -> Optional[Dict[str, Any]]:
    """
    Encodes attributes to a JSON-serializable dict.

    Args:
        attributes: The attributes to encode

    Returns:
        A dict of encoded attributes, or None if there are no attributes
    """
    if not attributes:
        return None

    encoded_attributes = {}
    for key, value in attributes.items():
        # pylint: disable=broad-exception-caught
        try:
            encoded_value = _encode_value(value)
            encoded_attributes[key] = encoded_value
        except Exception as error:
            _logger.exception("Failed to encode key %s: %s", key, error)

    return encoded_attributes if encoded_attributes else None


def _get_resource_data(
    sdk_resource_scope_data: Dict[Resource, _ResourceDataT],
    resource_class: Callable[..., _TypingResourceT],
    name: str,
) -> List[_TypingResourceT]:
    """
    Transforms SDK resource scope data into resource data for JSON format.

    Args:
        sdk_resource_scope_data: The SDK resource scope data
        resource_class: A function to create a resource class instance
        name: The name of the scope

    Returns:
        A list of resource class instances
    """
    resource_data = []

    for (
        sdk_resource,
        scope_data,
    ) in sdk_resource_scope_data.items():
        json_resource = _encode_resource(sdk_resource)
        resource_data.append(
            resource_class(
                **{
                    "resource": json_resource,
                    f"scope_{name}": list(scope_data.values()),
                }
            )
        )
    return resource_data


def _create_exp_backoff_generator(
    init_value: float = 1, max_value: float = float("inf")
) -> Generator[float, None, None]:
    """Generator for exponential backoff with random jitter.

    Args:
        init_value: initial backoff value in seconds
        max_value: maximum backoff value in seconds

    Returns:
        A generator that yields a random backoff value between 0 and
        min(init_value * 2 ** n, max_value) where n is the number of
        times the generator has been called so far.

    Example:
        >>> gen = _create_exp_backoff_generator(1, 10)
        >>> next(gen)  # Random value between 0 and 1
        >>> next(gen)  # Random value between 0 and 2
        >>> next(gen)  # Random value between 0 and 4
        >>> next(gen)  # Random value between 0 and 8
        >>> next(gen)  # Random value between 0 and 10
        >>> next(gen)  # Random value between 0 and 10
    """
    curr = init_value
    while True:
        yield curr
        curr = min(curr * 2, max_value)
