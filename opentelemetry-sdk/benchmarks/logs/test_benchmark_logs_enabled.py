# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import gc
import os
import tracemalloc
from unittest import mock

import pytest

from opentelemetry._logs import LogRecord, SeverityNumber
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


def _emit_log_record_unguarded(logger, index):
    logger.emit(
        LogRecord(
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
    )


def _emit_log_record_guarded(logger, index):
    if logger.enabled(severity_number=SeverityNumber.INFO, event_name="test.event"):
        logger.emit(
            LogRecord(
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
        )


_EMIT_FUNCTIONS = {
    ("kwargs", False): _emit_unguarded,
    ("kwargs", True): _emit_guarded,
    ("log_record", False): _emit_log_record_unguarded,
    ("log_record", True): _emit_log_record_guarded,
}


def _measure_allocations(benchmark, emit, logger):
    for index in range(100):
        emit(logger, index)

    peaks = []
    for index in range(200):
        tracemalloc.start()
        emit(logger, index)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peaks.append(peak)
    benchmark.extra_info["mean_alloc_bytes"] = sum(peaks) / len(peaks)

    # Measure gen-0 collections before/after emitting 10,000 log records
    gc.collect()
    collections_before = gc.get_stats()[0]["collections"]
    for index in range(10_000):
        emit(logger, index)
    benchmark.extra_info["gc_gen0_collections_per_10k"] = gc.get_stats()[0]["collections"] - collections_before


@pytest.mark.parametrize("guarded", [False, True], ids=["unguarded", "guarded"])
@pytest.mark.parametrize("style", ["kwargs", "log_record"])
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
def test_disabled_emit(benchmark, mechanism, style, guarded):
    benchmark.group = f"disabled-{mechanism}-{style}"
    logger = _make_disabled_logger(mechanism)
    emit = _EMIT_FUNCTIONS[(style, guarded)]
    _measure_allocations(benchmark, emit, logger)

    benchmark(emit, logger, 42)


@pytest.mark.parametrize("guarded", [False, True], ids=["unguarded", "guarded"])
def test_enabled_emit(benchmark, guarded):
    benchmark.group = "enabled-guard-overhead"
    provider = LoggerProvider(shutdown_on_exit=False)
    provider.add_log_record_processor(_SeverityFilteringProcessor(SeverityNumber.INFO))
    logger = provider.get_logger("bench")
    emit = _emit_guarded if guarded else _emit_unguarded

    benchmark(emit, logger, 42)
