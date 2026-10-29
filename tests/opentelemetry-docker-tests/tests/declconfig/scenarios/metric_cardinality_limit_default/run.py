# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import metrics

requests = metrics.get_meter("declconfig.cardinality").create_counter("requests")

for request_id in range(2100):
    requests.add(1, {"request.id": request_id})
