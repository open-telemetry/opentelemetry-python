# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import dataclasses
import fnmatch
import logging
import os
import uuid
from collections.abc import Callable
from typing import Any
from urllib import parse

from opentelemetry.sdk._configuration._common import load_entry_point
from opentelemetry.sdk._configuration.models import (
    AttributeNameValue,
    AttributeType,
    ExperimentalResourceDetector,
    IncludeExclude,
)
from opentelemetry.sdk._configuration.models import Resource as ResourceConfig
from opentelemetry.sdk.resources import (
    _DEFAULT_RESOURCE,
    OTEL_SERVICE_NAME,
    SERVICE_INSTANCE_ID,
    SERVICE_NAME,
    ProcessResourceDetector,
    Resource,
    _HostResourceDetector,
)
from opentelemetry.util.types import AttributeValue

_logger = logging.getLogger(__name__)


def _coerce_bool(value: object) -> bool:
    if isinstance(value, str):
        return value.lower() not in ("false", "0", "")
    return bool(value)


def _array(coerce: Callable) -> Callable:
    return lambda value: [coerce(item) for item in value]


# Dispatch table mapping AttributeType to its coercion callable
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


def create_resource(config: ResourceConfig | None) -> Resource:
    """Create an SDK Resource from declarative config.

    Does NOT read OTEL_RESOURCE_ATTRIBUTES. Resource detectors are only run
    when explicitly listed under detection_development.detectors in the config.
    Starts from SDK telemetry defaults (telemetry.sdk.*), merges any detected
    attributes, then merges explicit config attributes on top (highest priority).

    Args:
        config: Resource config from the parsed config file, or None.

    Returns:
        A Resource with SDK defaults, optional detector attributes, and any
        config-specified attributes merged in priority order.
    """
    # Spec requires service.name to always be present; detectors and explicit
    # config attributes can override this default.
    base = _DEFAULT_RESOURCE.merge(Resource({SERVICE_NAME: "unknown_service"}))

    if config is None:
        return base

    # attributes_list is lower priority; explicit attributes overwrite conflicts.
    config_attrs: dict[str, object] = {}
    if config.attributes_list:
        config_attrs.update(_parse_attributes_list(config.attributes_list))

    if config.attributes:
        for attr in config.attributes:
            config_attrs[attr.name] = _coerce_attribute_value(attr)

    schema_url = config.schema_url

    # Run detectors only if detection_development is configured. Collect all
    # detected attributes, apply the include/exclude filter, then merge before
    # config attributes so explicit values always win.
    result = base
    if config.detection_development:
        detected_attrs: dict[str, object] = {}
        if config.detection_development.detectors:
            for detector_config in config.detection_development.detectors:
                _run_detectors(detector_config, detected_attrs)

        filtered = _filter_attributes(
            detected_attrs, config.detection_development.attributes
        )
        if filtered:
            result = result.merge(Resource(filtered))  # type: ignore[arg-type]

    config_resource = Resource(config_attrs, schema_url)  # type: ignore[arg-type]
    return result.merge(config_resource)


def _detect_service(_config: Any) -> dict[str, AttributeValue]:
    """Service detector: generates instance ID and reads OTEL_SERVICE_NAME."""
    attrs: dict[str, AttributeValue] = {
        SERVICE_INSTANCE_ID: str(uuid.uuid4()),
    }
    if service_name := os.environ.get(OTEL_SERVICE_NAME):
        attrs[SERVICE_NAME] = service_name
    return attrs


_RESOURCE_DETECTOR_REGISTRY: dict[
    str, Callable[[Any], dict[str, AttributeValue]]
] = {
    "service": _detect_service,
    "host": lambda _: dict(_HostResourceDetector().detect().attributes),
    "process": lambda _: dict(ProcessResourceDetector().detect().attributes),
}


def _run_detectors(
    detector_config: ExperimentalResourceDetector,
    detected_attrs: dict[str, object],
) -> None:
    """Run detectors present in a single detector config entry.

    Known detectors (service, host, process) are handled directly via
    _RESOURCE_DETECTOR_REGISTRY. All other detectors — including known
    schema fields like container that require contrib packages, and
    unknown plugin detectors captured in additional_properties — are
    loaded via the ``opentelemetry_resource_detector`` entry point group.

    The detected_attrs dict is updated in-place; later detectors overwrite
    earlier ones for the same key.
    """
    for name in dataclasses.fields(detector_config):
        value = getattr(detector_config, name.name, None)
        if value is None:
            continue
        if name.name in _RESOURCE_DETECTOR_REGISTRY:
            detected_attrs.update(
                _RESOURCE_DETECTOR_REGISTRY[name.name](value)
            )
        else:
            cls = load_entry_point(
                "opentelemetry_resource_detector", name.name
            )
            detected_attrs.update(cls(**(value or {})).detect().attributes)

    for name, plugin_config in detector_config.additional_properties.items():
        cls = load_entry_point("opentelemetry_resource_detector", name)
        detected_attrs.update(cls(**(plugin_config or {})).detect().attributes)


def _filter_attributes(
    attrs: dict[str, object], filter_config: IncludeExclude | None
) -> dict[str, object]:
    """Filter detected attribute keys using include/exclude glob patterns.

    Mirrors other SDK IncludeExcludePredicate.createPatternMatching behaviour:
    - No filter config (attributes absent) → include all detected attributes.
    - included patterns are checked first; excluded patterns are applied after.
    - An empty included list is treated as "include everything".
    """
    if filter_config is None:
        return attrs

    included = filter_config.included
    excluded = filter_config.excluded

    if not included and not excluded:
        return attrs

    result: dict[str, object] = {}
    for key, value in attrs.items():
        if included and not any(fnmatch.fnmatch(key, pat) for pat in included):
            continue
        if excluded and any(fnmatch.fnmatch(key, pat) for pat in excluded):
            continue
        result[key] = value
    return result
