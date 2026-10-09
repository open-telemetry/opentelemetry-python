# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import metrics
from opentelemetry.metrics import Observation

meter = metrics.get_meter("declconfig.metrics")

meter.create_counter("requests").add(3, {"route": "/a"})
queue_size = meter.create_up_down_counter("queue.size")
queue_size.add(5)
queue_size.add(-2)
latency = meter.create_histogram("latency", unit="ms")
latency.record(10)
latency.record(20)
meter.create_gauge("temperature").set(21.5)
meter.create_observable_counter("cpu.time", [lambda options: [Observation(7)]])
meter.create_observable_gauge("memory.usage", [lambda options: [Observation(1024)]])
meter.create_observable_up_down_counter("connections", [lambda options: [Observation(4)]])
