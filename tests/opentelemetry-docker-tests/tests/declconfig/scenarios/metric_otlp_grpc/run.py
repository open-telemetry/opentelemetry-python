# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import metrics

metrics.get_meter(__name__).create_counter("grpc.requests").add(1)
