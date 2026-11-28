# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import logging
from logging import getLogger
from os import environ

from opentelemetry.sdk.environment_variables import OTEL_LOG_LEVEL

_logger = getLogger(__name__)

_LOG_LEVEL_MAP: dict[str, int] = {
    "error": logging.ERROR,
    "warn": logging.WARNING,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}


def parse_log_level_environment_variable(
    environment_variable: str,
    default: int | None = None,
) -> int | None:
    value = environ.get(environment_variable)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in _LOG_LEVEL_MAP:
        return _LOG_LEVEL_MAP[normalized]

    _logger.warning(
        "Invalid value for %s: %r. Expected one of %s.",
        environment_variable,
        value,
        ", ".join(sorted(_LOG_LEVEL_MAP)),
    )
    return default


def configure_sdk_log_level() -> None:
    if OTEL_LOG_LEVEL not in environ:
        return
    level = parse_log_level_environment_variable(
        OTEL_LOG_LEVEL,
        default=logging.INFO,
    )
    if level is not None:
        logging.getLogger("opentelemetry").setLevel(level)


def parse_boolean_environment_variable(environment_variable: str, default: bool = False) -> bool:
    value = environ.get(environment_variable)
    if value is None:
        return default

    match value.strip().lower():
        case "true":
            return True
        case "false":
            return False
        case _:
            _logger.warning(
                "Invalid value for %s: %r. Expected 'true' or 'false'.",
                environment_variable,
                value,
            )
            return default
