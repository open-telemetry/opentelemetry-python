# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Exceptions raised by the metrics SDK.

``MetricsTimeoutError`` is re-exported as
``opentelemetry.sdk.metrics.MetricsTimeoutError``, which is the name
application code should catch. It is raised in two places. The first is
``MeasurementConsumer.collect``, when an asynchronous callback overruns the
deadline, and it propagates out of ``MetricReader.collect`` and
``MetricReader.force_flush`` from there. The second is
``MeterProvider.force_flush``, which raises it and then catches it two lines
later and re-raises a plain ``Exception``, so it never escapes that method.
No shutdown path raises it at all: ``MeterProvider.shutdown`` reports a
deadline overrun as a plain ``Exception``.
"""


class MetricsTimeoutError(Exception):
    """Raised when a metrics function times out"""
