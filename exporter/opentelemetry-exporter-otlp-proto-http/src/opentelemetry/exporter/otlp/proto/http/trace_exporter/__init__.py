# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import sys as _sys
import opentelemetry.exporter.otlp._proto.http.trace_exporter as _mod

_sys.modules[__name__] = _mod
