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
from typing import Callable, Optional
from urllib import parse

from opentelemetry.sdk._configuration.models import (
    AttributeNameValue,
    AttributeType,
)
from opentelemetry.sdk._configuration.models import Resource as ResourceConfig
from opentelemetry.sdk.resources import (
    _DEFAULT_RESOURCE,
    SERVICE_NAME,
    Resource,
)

_logger = logging.getLogger(__name__)


def _coerce_bool(value: object) -> bool:
    if isinstance(value, str):
        return value.lower() not in ("false", "0", "")
    return bool(value)


def _array(coerce: Callable) -> Callable:
    return lambda value: [coerce(item) for item in value]


# Unified dispatch table for all attribute type coercions
_COERCIONS = {
    AttributeType.string: str,
    AttributeType.int: int,
    AttributeType.double: float,
    AttributeType.bool: _coerce_bool,
    AttributeType.string_array: _array(str),
    AttributeType.int_array: _array(int),
    AttributeType.double_array: _array(float),
    AttributeType.bool_array: _array(_coerce_bool),
}


def _coerce_attribute_value(attr: AttributeNameValue) -> object:
    """Coerce an attribute value to the correct Python type based on AttributeType."""
    coerce = _COERCIONS.get(attr.type)  # type: ignore[arg-type]
    return coerce(attr.value) if coerce is not None else attr.value  # type: ignore[operator]


def _parse_attributes_list(attributes_list: str) -> dict[str, str]:
    """Parse a comma-separated key=value string into a dict.

    Format is the same as OTEL_RESOURCE_ATTRIBUTES: key=value,key=value
    Values are always strings (no type coercion).
    """
    result: dict[str, str] = {}
    for item in attributes_list.split(","):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            _logger.warning(
                "Invalid resource attribute pair in attributes_list: %s",
                item,
            )
            continue
        key, value = item.split("=", maxsplit=1)
        result[key.strip()] = parse.unquote(value.strip())
    return result


def create_resource(config: Optional[ResourceConfig]) -> Resource:
    """Create an SDK Resource from declarative config.

    Does NOT read OTEL_RESOURCE_ATTRIBUTES or run any resource detectors.
    Starts from SDK telemetry defaults (telemetry.sdk.*) and merges config
    attributes on top, matching Java SDK behavior.

    Args:
        config: Resource config from the parsed config file, or None.

    Returns:
        A Resource with SDK defaults merged with any config-specified attributes.
    """
    base = _DEFAULT_RESOURCE

    if config is None:
        service_resource = Resource({SERVICE_NAME: "unknown_service"})
        return base.merge(service_resource)

    # attributes_list is lower priority; process it first so that explicit
    # attributes can simply overwrite any conflicting keys.
    config_attrs: dict[str, object] = {}
    if config.attributes_list:
        config_attrs.update(_parse_attributes_list(config.attributes_list))

    if config.attributes:
        for attr in config.attributes:
            config_attrs[attr.name] = _coerce_attribute_value(attr)

    schema_url = config.schema_url

    config_resource = Resource(config_attrs, schema_url)  # type: ignore[arg-type]
    result = base.merge(config_resource)

    # Add default service.name if not specified (matches Java SDK behavior)
    if not result.attributes.get(SERVICE_NAME):
        result = result.merge(Resource({SERVICE_NAME: "unknown_service"}))

    return result
