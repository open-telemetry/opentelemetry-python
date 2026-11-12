# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import metrics

meter = metrics.get_meter("declconfig.cardinality")
requests = meter.create_counter("requests")
other = meter.create_counter("other")
filtered = meter.create_counter("filtered")

for route in range(10):
    requests.add(1, {"route": f"/{route}"})
    other.add(1, {"route": f"/{route}"})

for route in range(2):
    for user in range(10):
        filtered.add(1, {"route": f"/{route}", "user": f"user-{user}"})
