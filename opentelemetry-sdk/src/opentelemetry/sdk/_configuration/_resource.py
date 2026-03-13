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
    Resource as ResourceConfig,
)
from opentelemetry.sdk.resources import (
    SERVICE_NAME,
    TELEMETRY_SDK_LANGUAGE,
    TELEMETRY_SDK_NAME,
    TELEMETRY_SDK_VERSION,
    Resource,
    _OPENTELEMETRY_SDK_VERSION,
)

_logger = logging.getLogger(__name__)


def _coerce_attribute_value(attr: AttributeNameValue) -> object:
    """Coerce an attribute value to the correct Python type based on AttributeType."""
    value = attr.value
    attr_type = attr.type

    if attr_type is None:
        return value

    if attr_type == AttributeType.string:
        return str(value)
    if attr_type == AttributeType.bool:
        if isinstance(value, str):
            return value.lower() not in ("false", "0", "")
        return bool(value)
    if attr_type == AttributeType.int:
        return int(value)  # type: ignore[arg-type]
    if attr_type == AttributeType.double:
        return float(value)  # type: ignore[arg-type]
    if attr_type == AttributeType.string_array:
        return [str(v) for v in value]  # type: ignore[union-attr]
    if attr_type == AttributeType.bool_array:
        return [bool(v) for v in value]  # type: ignore[union-attr]
    if attr_type == AttributeType.int_array:
        return [int(v) for v in value]  # type: ignore[union-attr,arg-type]
    if attr_type == AttributeType.double_array:
        return [float(v) for v in value]  # type: ignore[union-attr,arg-type]

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


def _sdk_default_attributes() -> dict[str, object]:
    """Return the SDK telemetry attributes (equivalent to Java's Resource.getDefault())."""
    return {
        TELEMETRY_SDK_LANGUAGE: "python",
        TELEMETRY_SDK_NAME: "opentelemetry",
        TELEMETRY_SDK_VERSION: _OPENTELEMETRY_SDK_VERSION,
    }


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
    base = Resource(_sdk_default_attributes())

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
        for k, v in list_attrs.items():
            if k not in config_attrs:
                config_attrs[k] = v

    schema_url = config.schema_url

    config_resource = Resource(config_attrs, schema_url)  # type: ignore[arg-type]
    result = base.merge(config_resource)

    # Add default service.name if not specified (matches Java SDK behavior)
    if not result.attributes.get(SERVICE_NAME):
        result = result.merge(Resource({SERVICE_NAME: "unknown_service"}))

    return result
