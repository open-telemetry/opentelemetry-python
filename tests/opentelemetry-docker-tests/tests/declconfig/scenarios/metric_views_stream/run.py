# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import metrics

meter = metrics.get_meter("declconfig.views", version="1.0")
meter.create_counter("requests", unit="1").add(1, {"route": "/a", "method": "GET"})
meter.create_counter("unmatched").add(1)
