# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# These tests import the real exporter via the public
# opentelemetry.exporter.otlp.proto.http path and the pure-Python exporter via
# the private opentelemetry.exporter.otlp._proto.http path. Guard that the public
# path resolves to the real protobuf distribution, not this package's shim.
from opentelemetry.exporter.otlp.proto.http import trace_exporter as _pub

assert "pyproto" not in (_pub.__file__ or ""), (
    "opentelemetry.exporter.otlp.proto.http resolved to the pyproto shim "
    f"({_pub.__file__}); equivalence tests need the real proto-http package."
)
