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

# Pinned commit/branch/tag for the current version used in opentelemetry-proto python package.
PROTO_REPO_BRANCH_OR_COMMIT="v0.4.0"

set -e

if [ -z "$VIRTUAL_ENV" ]; then
    echo '$VIRTUAL_ENV is not set, you probably forgot to source it. Exiting...'
    exit 1
fi

PROTO_REPO_DIR=${PROTO_REPO_DIR:-"/tmp/opentelemetry-proto"}
# root of opentelemetry-python repo
repo_root="$(git rev-parse --show-toplevel)"

python -m pip install -r $repo_root/dev-requirements.txt

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

cd $repo_root/opentelemetry-proto/src

# clean up old generated code
find opentelemetry/ -regex ".*_pb2.*\.pyi?" -exec rm {} +

# generate proto code for all protos
all_protos=$(find $PROTO_REPO_DIR/ -iname "*.proto")
python -m grpc_tools.protoc \
    -I $PROTO_REPO_DIR \
    --python_out=. \
    --mypy_out=. \
    $all_protos

# generate grpc output only for protos with service definitions
service_protos=$(grep -REl "service \w+ {" $PROTO_REPO_DIR/opentelemetry/)
python -m grpc_tools.protoc \
    -I $PROTO_REPO_DIR \
    --python_out=. \
    --mypy_out=. \
    --grpc_python_out=. \
    $service_protos
