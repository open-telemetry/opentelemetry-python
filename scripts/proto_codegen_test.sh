#!/bin/bash
#
# Regenerate the protobuf-backed reference classes under
# opentelemetry.proto._test from the OTLP protos in
# https://github.com/open-telemetry/opentelemetry-proto
#
# These classes are used ONLY by tests that need to decode OTLP bytes or run a
# real gRPC server. Runtime code uses the pure-Python classes under
# opentelemetry._proto (see scripts/proto_codegen.sh, which is now a no-op for
# the runtime classes since they are hand-maintained). The _test classes live in
# a separate import path so both sets can coexist in one process.
#
# To use, update PROTO_REPO_BRANCH_OR_COMMIT below to the tag/commit you want to
# build off of, then run this script and commit the changes.
#
# Optional envars:
#   PROTO_REPO_DIR - path to an existing checkout of the opentelemetry-proto repo

# Keep this in sync with scripts/proto_codegen.sh.
PROTO_REPO_BRANCH_OR_COMMIT="v1.10.0"

set -e

repo_root="$(git rev-parse --show-toplevel)"
PROTO_REPO_DIR=${PROTO_REPO_DIR:-"/tmp/opentelemetry-proto"}
XFORM_DIR="$(mktemp -d)"
OUT_DIR="$repo_root/opentelemetry-proto/src"

protoc() {
    # Pin grpcio-tools via gen-requirements.txt so the generated code targets the
    # same protobuf major version the [test] extra pins (protobuf>=5, <8).
    uvx -c "$repo_root/gen-requirements.txt" \
        --python 3.12 \
        --from grpcio-tools \
        python -m grpc_tools.protoc "$@"
}

protoc --version

# Clone the proto repo if it doesn't exist.
if [ ! -d "$PROTO_REPO_DIR" ]; then
    git clone https://github.com/open-telemetry/opentelemetry-proto.git "$PROTO_REPO_DIR"
fi
(
    cd "$PROTO_REPO_DIR"
    git fetch --all
    git checkout "$PROTO_REPO_BRANCH_OR_COMMIT"
    git symbolic-ref -q HEAD && git pull --ff-only || true
)

# Copy the opentelemetry/proto tree under opentelemetry/proto/_test/, rewriting
# the import statement paths so the generated python imports resolve under the
# _test namespace. Only the import paths change; message field numbers (and thus
# the wire format) are untouched, so the _test classes serialize identically to
# the pure-Python ones.
mkdir -p "$XFORM_DIR/opentelemetry/proto/_test"
(
    cd "$PROTO_REPO_DIR/opentelemetry/proto"
    find . -name '*.proto' -print0
) | while IFS= read -r -d '' rel; do
    src="$PROTO_REPO_DIR/opentelemetry/proto/${rel#./}"
    dst="$XFORM_DIR/opentelemetry/proto/_test/${rel#./}"
    mkdir -p "$(dirname "$dst")"
    sed 's#import "opentelemetry/proto/#import "opentelemetry/proto/_test/#g' "$src" > "$dst"
done

# Remove any previously generated _test code, then regenerate.
find "$OUT_DIR/opentelemetry/proto/_test" -regex ".*_pb2.*\.pyi?" -exec rm {} + 2>/dev/null || true

all_protos=$(find "$XFORM_DIR" -iname "*.proto")
protoc -I "$XFORM_DIR" --python_out="$OUT_DIR" $all_protos

service_protos=$(grep -REl "service \w+ {" "$XFORM_DIR")
protoc -I "$XFORM_DIR" --python_out="$OUT_DIR" --grpc_python_out="$OUT_DIR" $service_protos

# The pure-Python runtime set does not include profiles; drop it from _test too
# so the two sets cover the same signals.
rm -rf "$OUT_DIR/opentelemetry/proto/_test/profiles" \
       "$OUT_DIR/opentelemetry/proto/_test/collector/profiles"

# Make every generated directory an importable package.
find "$OUT_DIR/opentelemetry/proto/_test" -type d | while read -r dir; do
    init="$dir/__init__.py"
    if [ ! -f "$init" ]; then
        printf '# Copyright The OpenTelemetry Authors\n# SPDX-License-Identifier: Apache-2.0\n' > "$init"
    fi
done

rm -rf "$XFORM_DIR"
echo "Regenerated opentelemetry.proto._test from OTLP $PROTO_REPO_BRANCH_OR_COMMIT."
