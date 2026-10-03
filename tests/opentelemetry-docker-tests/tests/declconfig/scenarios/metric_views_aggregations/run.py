# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import metrics

meter = metrics.get_meter(__name__)
meter.create_counter("dropped").add(1)
summed = meter.create_histogram("summed")
summed.record(10)
summed.record(20)
last = meter.create_counter("last")
last.add(1)
last.add(2)
for name in ("bucketed", "exponential"):
    histogram = meter.create_histogram(name)
    histogram.record(5)
    histogram.record(50)
