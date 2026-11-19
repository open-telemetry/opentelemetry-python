# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import metrics

meter = metrics.get_meter("declconfig.cardinality")
requests = meter.create_counter("requests")
latency = meter.create_histogram("latency")

for route in range(10):
    requests.add(1, {"route": f"/{route}"})
    latency.record(1, {"route": f"/{route}"})
