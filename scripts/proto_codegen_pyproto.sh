#!/bin/bash
#
# Regenerate the pure-Python, encode-only message classes under
# opentelemetry._proto from the OTLP protos in
# https://github.com/open-telemetry/opentelemetry-proto
#
# These classes are the runtime OTLP message types. They serialize to the
# protobuf wire format without depending on the protobuf package. The protobuf
# helpers they call live in opentelemetry._proto._pyprotobuf (hand-maintained),
# and the gRPC service stubs live alongside as hand-written *_pb2_grpc.py files;
# this script regenerates only the *_pb2.py message modules.
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
OUT_DIR="$(mktemp -d)"
DST="$repo_root/opentelemetry-proto/src"

protoc() {
    # The pyproto plugin (protoc-gen-pyproto) is provided by the local codegen
    # package. gen-requirements.txt pins grpcio-tools so the descriptor parsing
    # matches the other codegen scripts.
    uvx -c "$repo_root/gen-requirements.txt" \
        --python 3.12 \
        --from grpcio-tools \
        --with "$repo_root/codegen/opentelemetry-codegen-pyproto" \
        python -m grpc_tools.protoc "$@"
}

protoc --version

if [ ! -d "$PROTO_REPO_DIR" ]; then
    git clone https://github.com/open-telemetry/opentelemetry-proto.git "$PROTO_REPO_DIR"
fi
(
    cd "$PROTO_REPO_DIR"
    git fetch --all
    git checkout "$PROTO_REPO_BRANCH_OR_COMMIT"
    git symbolic-ref -q HEAD && git pull --ff-only || true
)

# The pure-Python runtime set does not include profiles; exclude them so the
# generated set matches the packaged modules.
all_protos=$(find "$PROTO_REPO_DIR/opentelemetry/proto" -iname "*.proto" | grep -v "/profiles/")

protoc -I "$PROTO_REPO_DIR" --pyproto_out="$OUT_DIR" $all_protos

# Copy only the generated message modules into the source tree. The __init__.py,
# _pyprotobuf, and *_pb2_grpc.py files are hand-maintained and left untouched.
find "$OUT_DIR" -name '*_pb2.py' ! -name '*_pb2_grpc.py' | while read -r generated; do
    rel="${generated#"$OUT_DIR"/}"
    mkdir -p "$DST/$(dirname "$rel")"
    cp "$generated" "$DST/$rel"
done

rm -rf "$OUT_DIR"
echo "Regenerated opentelemetry._proto message classes from OTLP $PROTO_REPO_BRANCH_OR_COMMIT."
