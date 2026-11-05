# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
"""Self-observability counters for the logs SDK.

Holds the one metric the ``Logger`` records about itself, the count of log
records it has created, and a do-nothing stand-in used when self-observability
is switched off. ``Logger.emit`` calls ``emit_log`` once per record, so the
stand-in exists to keep that call cheap in the default configuration.
"""

from typing import Protocol

from opentelemetry import metrics as metrics_api
from opentelemetry.semconv._incubating.metrics.otel_metrics import (
    create_otel_sdk_log_created,
)


class LoggerMetricsT(Protocol):
    """What ``Logger`` requires of the object it reports its own counts to."""

    def emit_log(self) -> None:
        """Record that one log record has been created."""


class NoOpLoggerMetrics:
    """Implementation of ``LoggerMetricsT`` that records nothing.

    Used when ``OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED`` is not set to true,
    which is the default. No instrument is created, so no meter provider is
    touched.
    """

    def emit_log(self) -> None:
        """Do nothing.

        Present so that ``Logger`` can call it unconditionally instead of
        testing whether self-observability is switched on.
        """


class LoggerMetrics:
    """Implementation of ``LoggerMetricsT`` backed by a real counter.

    Creates the ``otel.sdk.log.created`` counter on a meter named
    ``opentelemetry-sdk`` when it is built, so the instrument exists even
    before the first log record is emitted.

    Args:
        meter_provider: The provider to obtain the meter from. Pointing it at
            the same provider that exports application metrics is what makes
            these counts show up alongside them.
    """

    def __init__(self, meter_provider: metrics_api.MeterProvider) -> None:
        """Build the instance and create the counter.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        meter = meter_provider.get_meter("opentelemetry-sdk")
        self._created_logs = create_otel_sdk_log_created(meter)

    def emit_log(self) -> None:
        """Add one to the ``otel.sdk.log.created`` counter.

        Counts records the ``Logger`` accepted for processing. A record the
        processors later drop, because the queue was full or the processor was
        already shut down, has still been counted here.
        """
        self._created_logs.add(1)


def create_logger_metrics(
    meter_provider: metrics_api.MeterProvider,
    enabled: bool,
) -> LoggerMetricsT:
    """Pick the recording or the do-nothing implementation.

    Args:
        meter_provider: The provider the counter is created on. Ignored when
            ``enabled`` is false, so passing a provider costs nothing in the
            default configuration.
        enabled: Whether to record at all. ``LoggerProvider`` passes the parsed
            value of ``OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED``.

    Returns:
        A ``LoggerMetrics`` when ``enabled`` is true, otherwise a
        ``NoOpLoggerMetrics``. The choice is made once, at ``LoggerProvider``
        construction, and cannot be changed afterwards.
    """
    if not enabled:
        return NoOpLoggerMetrics()

    return LoggerMetrics(meter_provider)
