# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import sys as _sys
import opentelemetry.exporter.otlp._proto.grpc.metric_exporter as _mod

_sys.modules[__name__] = _mod
