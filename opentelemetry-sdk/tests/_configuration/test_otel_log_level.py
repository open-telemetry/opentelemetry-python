# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging

import pytest

from opentelemetry.sdk._configuration import _configure_otel_log_level
from opentelemetry.sdk.environment_variables import OTEL_LOG_LEVEL

_OTel_LOGGER = "opentelemetry"


@pytest.fixture(autouse=True)
def _reset_otel_logger():
    """Restore the opentelemetry logger's level after each test."""
    logger = logging.getLogger(_OTel_LOGGER)
    original = logger.level
    yield
    logger.setLevel(original)


def test_debug_sets_debug_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(OTEL_LOG_LEVEL, "debug")
    _configure_otel_log_level()
    assert logging.getLogger(_OTel_LOGGER).level == logging.DEBUG


def test_info_sets_info_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(OTEL_LOG_LEVEL, "info")
    _configure_otel_log_level()
    assert logging.getLogger(_OTel_LOGGER).level == logging.INFO


def test_warn_sets_warning_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(OTEL_LOG_LEVEL, "warn")
    _configure_otel_log_level()
    assert logging.getLogger(_OTel_LOGGER).level == logging.WARNING


def test_warning_sets_warning_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(OTEL_LOG_LEVEL, "warning")
    _configure_otel_log_level()
    assert logging.getLogger(_OTel_LOGGER).level == logging.WARNING


def test_error_sets_error_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(OTEL_LOG_LEVEL, "error")
    _configure_otel_log_level()
    assert logging.getLogger(_OTel_LOGGER).level == logging.ERROR


def test_critical_sets_critical_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(OTEL_LOG_LEVEL, "critical")
    _configure_otel_log_level()
    assert logging.getLogger(_OTel_LOGGER).level == logging.CRITICAL


def test_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(OTEL_LOG_LEVEL, "DEBUG")
    _configure_otel_log_level()
    assert logging.getLogger(_OTel_LOGGER).level == logging.DEBUG


def test_unset_does_not_change_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(OTEL_LOG_LEVEL, raising=False)
    logging.getLogger(_OTel_LOGGER).setLevel(logging.WARNING)
    _configure_otel_log_level()
    assert logging.getLogger(_OTel_LOGGER).level == logging.WARNING


def test_invalid_value_warns_and_leaves_level(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv(OTEL_LOG_LEVEL, "verbose")
    logging.getLogger(_OTel_LOGGER).setLevel(logging.WARNING)
    with caplog.at_level(logging.WARNING):
        _configure_otel_log_level()
    assert logging.getLogger(_OTel_LOGGER).level == logging.WARNING
    assert any("verbose" in rec.message for rec in caplog.records)
