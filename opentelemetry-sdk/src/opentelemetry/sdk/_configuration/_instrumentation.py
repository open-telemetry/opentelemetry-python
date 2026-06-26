# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging

from opentelemetry.sdk._configuration.models import ExperimentalInstrumentation
from opentelemetry.util._importlib_metadata import entry_points

_logger = logging.getLogger(__name__)


def configure_instrumentation(
    config: ExperimentalInstrumentation | None,
) -> None:
    """Activate instrumentors listed under ``instrumentation/development.python``.

    For each entry in ``config.python`` the matching ``opentelemetry_instrumentor``
    entry point is loaded and ``instrument(**opts)`` is called on it. An
    ``enabled: false`` value in the options dict suppresses instrumentation for
    that library without raising an error.

    Absent or unknown entry points are logged as warnings; runtime errors from
    an instrumentor are logged as exceptions. Neither stops the remaining
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
            ep = next(
                iter(entry_points(group="opentelemetry_instrumentor", name=name))
            )
        except StopIteration:
            _logger.warning(
                "Instrumentation '%s' requested in declarative config but no "
                "'opentelemetry_instrumentor' entry point with that name was found; "
                "skipping",
                name,
            )
            continue

        try:
            ep.load()().instrument(**opts)
            _logger.debug("Instrumented '%s' via declarative config", name)
        except Exception:  # pylint: disable=broad-except
            _logger.exception(
                "Failed to instrument '%s' via declarative config", name
            )
