# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import inspect
from dataclasses import fields, is_dataclass
from logging import getLogger

from opentelemetry.sdk._configuration._common import load_entry_point
from opentelemetry.sdk._configuration._conversion import _dict_to_dataclass
from opentelemetry.sdk._configuration._exceptions import ConfigurationError
from opentelemetry.sdk._configuration.models import ExperimentalInstrumentation

_logger = getLogger(__name__)


def configure_instrumentation(
    configuration: ExperimentalInstrumentation | None,
) -> None:
    """Activate instrumentors listed under ``instrumentation/development.python``.

    For each entry in ``configuration.python`` the matching
    ``opentelemetry_instrumentor`` entry point is loaded.  If the instrumentor
    class exposes a ``configuration`` attribute that is a dataclass type, the
    raw options are validated through ``_dict_to_dataclass`` before being
    forwarded to ``instrument()``.  An ``enabled: false`` value suppresses
    instrumentation without raising.

    If an instrumentor is already active (e.g. ``opentelemetry-instrument``
    ran before the SDK was configured from the file) its ``instrument()`` call
    is skipped to avoid a double-instrumentation warning.

    Absent or unknown entry points are logged as warnings; runtime errors from
    an instrumentor are logged as exceptions.  Neither stops the remaining
    instrumentors from being applied.
    """
    if configuration is None or configuration.python is None:
        return

    for name, options in configuration.python.items():
        options = dict(options)
        if not options.pop("enabled", True):
            _logger.debug(
                "Instrumentation '%s' is disabled in declarative config; skipping",
                name,
            )
            continue

        try:
            cls = load_entry_point("opentelemetry_instrumentor", name)
            configuration_cls = getattr(cls, "configuration", None)
            if inspect.isclass(configuration_cls) and is_dataclass(
                configuration_cls
            ):
                configuration_obj = _dict_to_dataclass(
                    options, configuration_cls
                )
                options = {
                    f.name: value
                    for f in fields(configuration_obj)
                    if (value := getattr(configuration_obj, f.name))
                    is not None
                }
            instance = cls()
            if getattr(instance, "is_instrumented_by_opentelemetry", False):
                _logger.debug("Skipping '%s': already instrumented", name)
            else:
                instance.instrument(**options)
                _logger.debug("Instrumented '%s' via declarative config", name)
        except ConfigurationError as exc:
            _logger.warning(
                "Skipping instrumentation '%s' in declarative config: %s",
                name,
                exc,
            )
        except Exception:  # pylint: disable=broad-except
            _logger.exception(
                "Failed to instrument '%s' via declarative config", name
            )
