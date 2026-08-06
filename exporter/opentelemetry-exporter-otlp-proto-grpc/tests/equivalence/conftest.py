# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry.exporter.otlp.proto.grpc import trace_exporter as _pub

assert "pyproto" not in (_pub.__file__ or ""), (
    "opentelemetry.exporter.otlp.proto.grpc resolved to the pyproto shim "
    f"({_pub.__file__}); equivalence tests need the real proto-grpc package."
)
