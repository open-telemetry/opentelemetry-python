#!/bin/bash
#
# Regenerate python code from OTLP protos in
# https://github.com/open-telemetry/opentelemetry-proto
#
# Optional envars:
#   PROTO_REPO_DIR - the path to an existing checkout of the opentelemetry-proto repo
#   PROTO_REPO_BRANCH - the branch or commit to build from

set -ev

if [ -z "$VIRTUAL_ENV" ]; then
    echo '$VIRTUAL_ENV is not set, you probably forgot to source it. Exiting...'
    exit 1
fi

# TODO: should these live in dev-requirements.txt?
python -m pip install grpcio-tools==1.29.0 mypy-protobuf==1.21 protobuf==3.12.2

PROTO_REPO_DIR=${PROTO_REPO_DIR:-"/tmp/opentelemetry-proto"}
PROTO_REPO_BRANCH=${PROTO_REPO_BRANCH:-master}

# root of opentelemetry-python repo
repo_root="$(git rev-parse --show-toplevel)"

# Clone the proto repo if it doesn't exist
if [ ! -d "$PROTO_REPO_DIR" ]; then
    git clone https://github.com/open-telemetry/opentelemetry-proto.git $PROTO_REPO_DIR
fi

# Pull in changes and switch to requested branch
(
    cd $PROTO_REPO_DIR
    git fetch --all
    git checkout $PROTO_REPO_BRANCH 
    git pull --ff-only
)

cd $repo_root/opentelemetry-proto/src

# clean up old generated code
find opentelemetry/ -regex ".*_pb2.*\.pyi?" -exec rm {} +

python -m grpc_tools.protoc \
    -I $PROTO_REPO_DIR \
    --python_out=. \
    --mypy_out=. \
    `find $PROTO_REPO_DIR/ -iname "*.proto"`

# add grpc output for protos with service definitions
service_protos=$(grep -REl "service \w+ {" $PROTO_REPO_DIR/opentelemetry/)
echo $service_protos
python -m grpc_tools.protoc \
    -I $PROTO_REPO_DIR \
    --python_out=. \
    --mypy_out=. \
    --grpc_python_out=. \
    $service_protos

# opentelemetry-proto/src/opentelemetry/proto/collector/trace/v1/trace_service_pb2_grpc.py
# opentelemetry-proto/src/opentelemetry/proto/collector/metrics/v1/metrics_service_pb2_grpc.py
