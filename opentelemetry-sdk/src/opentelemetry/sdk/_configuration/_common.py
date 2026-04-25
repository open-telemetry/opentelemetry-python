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

import dataclasses
import inspect
import logging

from opentelemetry.sdk._configuration._exceptions import ConfigurationError
from opentelemetry.util._importlib_metadata import entry_points

_logger = logging.getLogger(__name__)


def _additional_properties(cls):
    """Decorator for dataclasses whose JSON Schema sets additionalProperties.

    Wraps the dataclass-generated ``__init__`` so that unknown keyword
    arguments are captured into an ``additional_properties`` instance
    attribute instead of raising ``TypeError``.  This lets plugin/custom
    component names flow through the config pipeline without modifying
    the codegen output for known fields.

    Applied automatically by the custom template in ``opentelemetry-sdk/codegen/``
    when ``additionalPropertiesType`` is present in the template context
    (set by ``datamodel-codegen`` for schema types with ``additionalProperties``).
    """
    original_init = cls.__init__
    original_sig = inspect.signature(original_init)
    known_fields = frozenset(f.name for f in dataclasses.fields(cls))

    def _init(self, **kwargs):
        known = {k: v for k, v in kwargs.items() if k in known_fields}
        extra = {k: v for k, v in kwargs.items() if k not in known_fields}
        original_init(self, **known)
        self.additional_properties = extra

    # Preserve the original parameter list for IDE autocompletion and
    # inspect.signature(), adding **kwargs to signal extras are accepted.
    # setattr used because pyright rejects direct __signature__ assignment.
    params = list(original_sig.parameters.values())
    params.append(inspect.Parameter("kwargs", inspect.Parameter.VAR_KEYWORD))
    setattr(_init, "__signature__", original_sig.replace(parameters=params))  # noqa: B010

    cls.__init__ = _init
    return cls


def load_entry_point(group: str, name: str) -> type:
    """Load a plugin class from an entry point group by name.

    Returns the loaded class — callers are responsible for instantiation
    with whatever arguments their config requires.

    Raises:
        ConfigurationError: If the entry point is not found or fails to load.
    """
    try:
        ep = next(iter(entry_points(group=group, name=name)), None)
        if ep is None:
            raise ConfigurationError(
                f"Plugin '{name}' not found in group '{group}'. "
                "Make sure the package providing this plugin is installed."
            )
        return ep.load()
    except ConfigurationError:
        raise
    except Exception as exc:
        raise ConfigurationError(
            f"Failed to load plugin '{name}' from group '{group}': {exc}"
        ) from exc


def _parse_headers(
    headers: list | None,
    headers_list: str | None,
) -> dict[str, str] | None:
    """Merge headers struct and headers_list into a dict.

    Returns None if neither is set, letting the exporter read env vars.
    headers struct takes priority over headers_list for the same key.
    """
    if headers is None and headers_list is None:
        return None
    result: dict[str, str] = {}
    if headers_list:
        for item in headers_list.split(","):
            item = item.strip()
            if "=" in item:
                key, value = item.split("=", 1)
                result[key.strip()] = value.strip()
            elif item:
                _logger.warning(
                    "Invalid header pair in headers_list (missing '='): %s",
                    item,
                )
    if headers:
        for pair in headers:
            result[pair.name] = pair.value or ""
    return result
