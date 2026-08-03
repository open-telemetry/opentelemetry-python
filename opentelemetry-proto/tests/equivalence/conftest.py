# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# The equivalence tests import the real (google.protobuf) message classes via
# ``opentelemetry.proto.*`` and the pure-Python classes via
# ``opentelemetry._proto.*``. Both this distribution (as a re-export shim) and
# the real ``opentelemetry-proto`` provide ``opentelemetry.proto``; guard that
# the public path resolves to the real package, not this package's shim, so the
# comparisons are genuinely real-vs-pure-Python.
from opentelemetry.proto.trace.v1 import trace_pb2 as _public_trace_pb2

assert "pyproto" not in (_public_trace_pb2.__file__ or ""), (
    "opentelemetry.proto resolved to the pyproto shim "
    f"({_public_trace_pb2.__file__}); the equivalence tests need the real "
    "opentelemetry-proto package to own that path."
)
