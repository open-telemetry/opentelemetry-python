#!/bin/bash
#
# Regenerate python code from Jaeger protos in
# https://github.com/jaegertracing/jaeger-idl
#

set +e

PROTO_REPO_DIR=${PROTO_REPO_DIR:-"/tmp/proto_codegen_jaeger"}
# root of opentelemetry-python repo
repo_root="$(git rev-parse --show-toplevel)"
venv_dir="/tmp/proto_codegen_jaeger_venv"

# run on exit even if crash
cleanup() {
    echo "Deleting $venv_dir"
    rm -rf $venv_dir
}
trap cleanup EXIT

echo "Creating temporary virtualenv at $venv_dir using $(python3 --version)"
python3 -m venv $venv_dir
source $venv_dir/bin/activate
python -m pip install \
    -c $repo_root/dev-requirements.txt \
    grpcio-tools mypy-protobuf

# Clone the proto repo if it doesn't exist
if [ ! -d "$PROTO_REPO_DIR" ]; then
    git clone https://github.com/jaegertracing/jaeger-idl.git ${PROTO_REPO_DIR}/jaeger-idl
    git clone https://github.com/grpc-ecosystem/grpc-gateway ${PROTO_REPO_DIR}/grpc-gateway
    git clone https://github.com/gogo/googleapis ${PROTO_REPO_DIR}/googleapis
    git clone https://github.com/gogo/protobuf ${PROTO_REPO_DIR}/protobuf
fi

DEST="exporter/opentelemetry-exporter-jaeger-proto-grpc/src/opentelemetry/exporter/jaeger/proto/grpc/gen"

mkdir -p ${DEST}

# protoc ${PROTO_INCLUDES} --grpc_python_out=./python_out --python_out=./python_out ${DIR}/model.proto
python -m grpc_tools.protoc \
    -I ${PROTO_REPO_DIR}/jaeger-idl/proto/api_v2 \
    -I ${PROTO_REPO_DIR}/grpc-gateway \
    -I ${PROTO_REPO_DIR}/googleapis \
    -I ${PROTO_REPO_DIR}/protobuf/protobuf \
    -I ${PROTO_REPO_DIR}/protobuf \
    --grpc_python_out=./${DEST} \
    --mypy_out=./${DEST} \
    --python_out=./${DEST} \
    ${PROTO_REPO_DIR}/jaeger-idl/proto/api_v2/model.proto ${PROTO_REPO_DIR}/jaeger-idl/proto/api_v2/collector.proto