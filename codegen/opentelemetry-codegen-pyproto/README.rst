opentelemetry-codegen-pyproto
=============================

A ``protoc`` plugin that generates pure-Python, encode-only protobuf-wire
message classes for the OpenTelemetry proto definitions.

The generated classes reproduce the behaviour of the hand-written
``opentelemetry._proto.*_pb2`` modules: every message inherits the
``Message`` base from ``opentelemetry._proto._pyprotobuf.message`` and
implements ``SerializeToString`` using the field helpers in
``opentelemetry._proto._pyprotobuf.fields``.

Usage
-----

Install the plugin so ``protoc-gen-pyproto`` is on ``PATH``, then run::

    python -m grpc_tools.protoc \
        -I /path/to/opentelemetry-proto \
        --pyproto_out=OUTPUT_DIR \
        /path/to/opentelemetry-proto/opentelemetry/proto/common/v1/common.proto
