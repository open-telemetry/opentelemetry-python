# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging

import pytest

from opentelemetry.sdk._configuration import _configure_otel_log_level
from opentelemetry.sdk.environment_variables import OTEL_LOG_LEVEL

_OTEL_LOGGER = "opentelemetry"


@pytest.fixture(autouse=True)
def reset_otel_logger():
    logger = logging.getLogger(_OTEL_LOGGER)
    original_level = logger.level
    yield
    logger.setLevel(original_level)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("debug", logging.DEBUG),
        ("INFO", logging.INFO),
        ("warn", logging.WARNING),
        ("warning", logging.WARNING),
        ("error", logging.ERROR),
        ("critical", logging.CRITICAL),
    ],
)
def test_valid_value_sets_otel_logger_level(value, expected, monkeypatch):
    monkeypatch.setenv(OTEL_LOG_LEVEL, value)

    _configure_otel_log_level()

    assert logging.getLogger(_OTEL_LOGGER).level == expected


def test_empty_value_does_not_change_otel_logger_level(monkeypatch):
    monkeypatch.setenv(OTEL_LOG_LEVEL, " ")
    logger = logging.getLogger(_OTEL_LOGGER)
    logger.setLevel(logging.WARNING)

    _configure_otel_log_level()

    assert logger.level == logging.WARNING


def test_unset_value_does_not_change_otel_logger_level(monkeypatch):
    monkeypatch.delenv(OTEL_LOG_LEVEL, raising=False)
    logger = logging.getLogger(_OTEL_LOGGER)
    logger.setLevel(logging.WARNING)

    _configure_otel_log_level()

    assert logger.level == logging.WARNING


def test_invalid_value_warns_and_does_not_change_otel_logger_level(monkeypatch, caplog):
    monkeypatch.setenv(OTEL_LOG_LEVEL, "verbose")
    logger = logging.getLogger(_OTEL_LOGGER)
    logger.setLevel(logging.WARNING)

    with caplog.at_level(logging.WARNING):
        _configure_otel_log_level()

    assert logger.level == logging.WARNING
    assert any("verbose" in record.message for record in caplog.records)
