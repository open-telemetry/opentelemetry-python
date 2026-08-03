# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry.exporter.otlp._proto.grpc import *  # noqa: F401,F403
import opentelemetry.exporter.otlp._proto.grpc as _src

for _n in dir(_src):
    if not _n.startswith('__'):
        globals().setdefault(_n, getattr(_src, _n))
del _src, _n
