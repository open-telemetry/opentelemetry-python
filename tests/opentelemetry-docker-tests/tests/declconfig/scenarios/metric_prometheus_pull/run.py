# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import time

from opentelemetry import metrics

requests = metrics.get_meter(__name__).create_counter("prom.requests")
# Keep serving until the harness stops the app.
while True:
    requests.add(1)
    time.sleep(0.5)
