# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import dataclasses
import logging

from opentelemetry.sdk._configuration._common import load_entry_point
from opentelemetry.sdk._configuration._conversion import _dict_to_dataclass
from opentelemetry.sdk._configuration._exceptions import ConfigurationError
from opentelemetry.sdk._configuration.models import ExperimentalInstrumentation

_logger = logging.getLogger(__name__)


def configure_instrumentation(
    config: ExperimentalInstrumentation | None,
) -> None:
    """Activate instrumentors listed under ``instrumentation/development.python``.

    For each entry in ``config.python`` the matching ``opentelemetry_instrumentor``
    entry point is loaded.  If the instrumentor class exposes a
    ``config_dataclass`` attribute, the raw options are validated through
    ``_dict_to_dataclass`` before being forwarded to ``instrument()``.
    An ``enabled: false`` value suppresses instrumentation without raising.

    Absent or unknown entry points are logged as warnings; runtime errors from
    an instrumentor are logged as exceptions.  Neither stops the remaining
    instrumentors from being applied.
    """
    if config is None or config.python is None:
        return

    for name, opts in config.python.items():
        opts = dict(opts)
        if not opts.pop("enabled", True):
            _logger.debug(
                "Instrumentation '%s' is disabled in declarative config; skipping",
                name,
            )
            continue

        try:
            cls = load_entry_point("opentelemetry_instrumentor", name)
            config_cls = getattr(cls, "config_dataclass", None)
            if config_cls is not None:
                config_obj = _dict_to_dataclass(opts, config_cls)
                opts = {
                    f.name: v
                    for f in dataclasses.fields(config_obj)
                    if (v := getattr(config_obj, f.name)) is not None
                }
            cls().instrument(**opts)
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
