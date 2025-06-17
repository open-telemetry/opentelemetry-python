#!/bin/bash
#
# Regenerate python code from OTLP protos in
# https://github.com/open-telemetry/opentelemetry-proto
#
# To use, update PROTO_REPO_BRANCH_OR_COMMIT variable below to a commit hash or
# tag in opentelemtry-proto repo that you want to build off of. Then, just run
# this script to update the proto files. Commit the changes as well as any
# fixes needed in the OTLP exporter.
#
# Optional envars:
#   PROTO_REPO_DIR - the path to an existing checkout of the opentelemetry-proto repo

set -euo pipefail

# Pinned commit/branch/tag for the current version used in opentelemetry-proto python package.
PROTO_REPO_BRANCH_OR_COMMIT="v1.2.0"
PROTO_REPO_DIR=${PROTO_REPO_DIR:-"$(mktemp -d)/opentelemetry-proto"}
# root of opentelemetry-python repo
REPO_ROOT="$(git rev-parse --show-toplevel)"
OUT_DIR="$REPO_ROOT/opentelemetry-proto/src"
#CLEAN_DIR="${OUT_DIR}/opentelemetry"
PYTHON_VERSION=3.13
PROTOC="uv run -p $PYTHON_VERSION \
        --no-project \
        --with-requirements $REPO_ROOT/gen-requirements.txt \
        python -m grpc_tools.protoc"

echo 'protoc --version'
$PROTOC --version

# Clone the proto repo if it doesn't exist
if [ ! -d "$PROTO_REPO_DIR" ]; then
    git clone https://github.com/open-telemetry/opentelemetry-proto.git $PROTO_REPO_DIR
fi

# Pull in changes and switch to requested branch
(
    cd $PROTO_REPO_DIR
    git fetch --all
    git checkout $PROTO_REPO_BRANCH_OR_COMMIT
    # pull if PROTO_REPO_BRANCH_OR_COMMIT is not a detached head
    git symbolic-ref -q HEAD && git pull --ff-only || true
)

# clean up old generated code
find $OUT_DIR -regex ".*_pb2.*\.pyi?" -exec rm {} +

# generate proto code for all protos
all_protos=$(find $PROTO_REPO_DIR/ -iname "*.proto")
$PROTOC \
    -I $PROTO_REPO_DIR \
    --python_out=$OUT_DIR \
    --mypy_out=$OUT_DIR \
    $all_protos

# generate grpc output only for protos with service definitions
service_protos=$(grep -REl "service \w+ {" $PROTO_REPO_DIR/opentelemetry/)

$PROTOC \
    -I $PROTO_REPO_DIR \
    --python_out=$OUT_DIR \
    --mypy_out=$OUT_DIR \
    --grpc_python_out=$OUT_DIR \
    $service_protos

echo "Please update ./opentelemetry-proto/README.rst to include the updated version."
