# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import metrics

metrics.get_meter("enabled.meter").create_counter("enabled.requests").add(1)
metrics.get_meter("disabled.meter").create_counter("disabled.requests").add(1)
