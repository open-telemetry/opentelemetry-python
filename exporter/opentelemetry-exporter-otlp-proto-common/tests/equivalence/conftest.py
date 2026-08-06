# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Equivalence tests import the real (protobuf) encoder via the public
# ``opentelemetry.exporter.otlp.proto.common`` path and the pure-Python encoder
# via the private ``opentelemetry.exporter.otlp._proto.common`` path. Both this
# package and the real ``opentelemetry-exporter-otlp-proto-common`` provide the
# public path, so guard that it resolves to the real protobuf distribution and
# not this package's own re-export shim -- otherwise the equivalence assertions
# would silently compare the pure-Python implementation against itself.
from opentelemetry.exporter.otlp.proto.common import (
    trace_encoder as _public_trace_encoder,
)

assert "pyproto" not in (_public_trace_encoder.__file__ or ""), (
    "opentelemetry.exporter.otlp.proto.common resolved to the pyproto shim "
    f"({_public_trace_encoder.__file__}); the equivalence tests need the real "
    "protobuf package to own that path."
)
