# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import metrics

latency = metrics.get_meter(__name__).create_histogram("latency", unit="ms")
latency.record(10)
latency.record(20)
