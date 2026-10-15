# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import os
from unittest import mock

import pytest

from opentelemetry._logs import SeverityNumber
from opentelemetry._logs._internal import ProxyLogger
from opentelemetry.sdk._logs import LoggerProvider, LogRecordProcessor
from opentelemetry.sdk._logs._internal import _disable_logger_configurator
from opentelemetry.sdk.environment_variables import OTEL_SDK_DISABLED


class _SeverityFilteringProcessor(LogRecordProcessor):
    """Processor that only accepts records at or above ``min_severity``.

    ``on_emit`` does no export work so the benchmarks measure the SDK
    overhead of creating and dispatching the record.
    """

    def __init__(self, min_severity):
        self._min_severity = min_severity

    def on_emit(self, log_record):
        pass

    def enabled(
        self,
        *,
        context=None,
        instrumentation_scope=None,
        severity_number=None,
        event_name=None,
    ):
        return severity_number is None or severity_number.value >= self._min_severity.value

    def shutdown(self):
        pass

    def force_flush(self, timeout_millis=30000):
        return True


def _make_disabled_logger(mechanism):
    """Returns a logger for which an INFO record is disabled."""
    if mechanism == "logger_config":
        provider = LoggerProvider(
            shutdown_on_exit=False,
            _logger_configurator=_disable_logger_configurator,
        )
        provider.add_log_record_processor(_SeverityFilteringProcessor(SeverityNumber.INFO))
        return provider.get_logger("bench")
    if mechanism == "processor_filter":
        provider = LoggerProvider(shutdown_on_exit=False)
        provider.add_log_record_processor(_SeverityFilteringProcessor(SeverityNumber.WARN))
        return provider.get_logger("bench")
    if mechanism == "no_processors":
        return LoggerProvider(shutdown_on_exit=False).get_logger("bench")
    if mechanism == "sdk_disabled":
        with mock.patch.dict(os.environ, {OTEL_SDK_DISABLED: "true"}):
            provider = LoggerProvider(shutdown_on_exit=False)
        return provider.get_logger("bench")
    if mechanism == "api_proxy_noop":
        return ProxyLogger("bench")
    raise ValueError(f"unknown mechanism: {mechanism}")


def _emit_unguarded(logger, index):
    logger.emit(
        severity_number=SeverityNumber.INFO,
        body=f"benchmark log message {index}",
        attributes={
            "http.request.method": "GET",
            "http.route": "/users/{id}",
            "http.response.status_code": 200,
            "user.id": index,
            "server.address": "example.com",
        },
        event_name="test.event",
    )


def _emit_guarded(logger, index):
    if logger.enabled(severity_number=SeverityNumber.INFO, event_name="test.event"):
        _emit_unguarded(logger, index)


@pytest.mark.parametrize("guarded", [False, True], ids=["unguarded", "guarded"])
@pytest.mark.parametrize(
    "mechanism",
    [
        "logger_config",
        "processor_filter",
        "no_processors",
        "sdk_disabled",
        "api_proxy_noop",
    ],
)
def test_disabled_emit(benchmark, mechanism, guarded):
    benchmark.group = f"disabled-{mechanism}"
    logger = _make_disabled_logger(mechanism)
    emit = _emit_guarded if guarded else _emit_unguarded

    benchmark(emit, logger, 42)


@pytest.mark.parametrize("guarded", [False, True], ids=["unguarded", "guarded"])
def test_enabled_emit(benchmark, guarded):
    benchmark.group = "enabled-guard-overhead"
    provider = LoggerProvider(shutdown_on_exit=False)
    provider.add_log_record_processor(_SeverityFilteringProcessor(SeverityNumber.INFO))
    logger = provider.get_logger("bench")
    emit = _emit_guarded if guarded else _emit_unguarded

    benchmark(emit, logger, 42)
