# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import time

from opentelemetry import metrics

requests = metrics.get_meter("declconfig.cardinality").create_counter("requests")


def record(batch):
    for route in range(10):
        requests.add(1, {"batch": batch, "route": f"/{route}"})


record("first")
# Wait for more than one export interval so the batches are collected separately.
time.sleep(2.5)
record("second")
