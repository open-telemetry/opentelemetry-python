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
from typing import Optional
from urllib import parse

from opentelemetry.sdk._configuration.models import (
    AttributeNameValue,
    AttributeType,
)
from opentelemetry.sdk._configuration.models import Resource as ResourceConfig
from opentelemetry.sdk.resources import (
    SERVICE_NAME,
    Resource,
    _DEFAULT_RESOURCE,
)

_logger = logging.getLogger(__name__)


def _coerce_bool(value: object) -> bool:
    if isinstance(value, str):
        return value.lower() not in ("false", "0", "")
    return bool(value)


# Dispatch table for scalar type coercions
_SCALAR_COERCIONS = {
    AttributeType.string: str,
    AttributeType.int: int,
    AttributeType.double: float,
    AttributeType.bool: _coerce_bool,
}

# Dispatch table for array type coercions
_ARRAY_COERCIONS = {
    AttributeType.string_array: str,
    AttributeType.bool_array: _coerce_bool,
    AttributeType.int_array: int,
    AttributeType.double_array: float,
}


def _coerce_attribute_value(attr: AttributeNameValue) -> object:
    """Coerce an attribute value to the correct Python type based on AttributeType."""
    value = attr.value
    attr_type = attr.type

    if attr_type is None:
        return value
    scalar_coercer = _SCALAR_COERCIONS.get(attr_type)
    if scalar_coercer is not None:
        return scalar_coercer(value)  # type: ignore[arg-type]
    array_coercer = _ARRAY_COERCIONS.get(attr_type)
    if array_coercer is not None:
        return [array_coercer(item) for item in value]  # type: ignore[union-attr,arg-type]
    return value


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

    # Build attributes from config.attributes list
    config_attrs: dict[str, object] = {}
    if config.attributes:
        for attr in config.attributes:
            config_attrs[attr.name] = _coerce_attribute_value(attr)

    # Parse attributes_list (key=value,key=value string format)
    if config.attributes_list:
        list_attrs = _parse_attributes_list(config.attributes_list)
        # attributes_list entries do not override explicit attributes
        for attr_key, attr_val in list_attrs.items():
            if attr_key not in config_attrs:
                config_attrs[attr_key] = attr_val

    schema_url = config.schema_url

    config_resource = Resource(config_attrs, schema_url)  # type: ignore[arg-type]
    result = base.merge(config_resource)

    # Add default service.name if not specified (matches Java SDK behavior)
    if not result.attributes.get(SERVICE_NAME):
        result = result.merge(Resource({SERVICE_NAME: "unknown_service"}))

    return result
