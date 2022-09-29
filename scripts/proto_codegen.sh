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
PROTO_REPO_BRANCH_OR_COMMIT="v0.17.0"

set -e

PROTO_REPO_DIR=${PROTO_REPO_DIR:-"/tmp/opentelemetry-proto"}
# root of opentelemetry-python repo
repo_root="$(git rev-parse --show-toplevel)"
venv_dir="/tmp/proto_codegen_venv"
generated_code_tmp_dir_1="/tmp/opentelemetry-proto-gen-1"
generated_code_tmp_dir_2="/tmp/opentelemetry-proto-gen-2"
mkdir -p $generated_code_tmp_dir_1 $generated_code_tmp_dir_2
# run on exit even if crash
cleanup() {
    echo "Deleting $venv_dir $generated_code_tmp_dir_1 $generated_code_tmp_dir_2"
    rm -rf $venv_dir $generated_code_tmp_dir_1 $generated_code_tmp_dir_2
}
trap cleanup EXIT

echo "Creating temporary virtualenv at $venv_dir using $(python3 --version)"
python3 -m venv $venv_dir
source $venv_dir/bin/activate

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

all_protos=$(find $PROTO_REPO_DIR/ -iname "*.proto")
service_protos=$(grep -REl "service \w+ {" $PROTO_REPO_DIR/opentelemetry/)

# First pass: generate protobuf with older version
python -m pip install grpcio-tools~=1.41.0 mypy-protobuf~=3.0.0

# generate mypy and grpc stubs
python -m grpc_tools.protoc \
    -I $PROTO_REPO_DIR \
    --mypy_out=. \
    $all_protos

# generate grpc output only for protos with service definitions
python -m grpc_tools.protoc \
    -I $PROTO_REPO_DIR \
    --mypy_out=. \
    --grpc_python_out=. \
    $service_protos

# generate proto code for all protos
python -m grpc_tools.protoc \
    -I $PROTO_REPO_DIR \
    --python_out=$generated_code_tmp_dir_1 \
    $all_protos

# generate grpc output only for protos with service definitions
python -m grpc_tools.protoc \
    -I $PROTO_REPO_DIR \
    --python_out=$generated_code_tmp_dir_1 \
    $service_protos

# Second pass: generate protobuf with newer version
python -m pip install "grpcio-tools>=1.49.0"
# generate proto code for all protos
python -m grpc_tools.protoc \
    -I $PROTO_REPO_DIR \
    --python_out=$generated_code_tmp_dir_2 \
    $all_protos

# generate grpc output only for protos with service definitions
python -m grpc_tools.protoc \
    -I $PROTO_REPO_DIR \
    --python_out=$generated_code_tmp_dir_2 \
    $service_protos

# Combine both version of protobuf
find $generated_code_tmp_dir_1/ -iname "*_pb2.py" |
while read -r old_proto_file; do 
    target=${PWD}/${old_proto_file/$generated_code_tmp_dir_1\/}
    new_proto_file=${old_proto_file/$generated_code_tmp_dir_1/$generated_code_tmp_dir_2}
    mkdir -p "$(dirname "$target")"
    {
        echo "from google.protobuf.internal.api_implementation import Type as _Type";
        echo "if _Type() == \"upb\":";
        sed 's/^/  /' "$new_proto_file";
        echo "else:";
        sed 's/^/  /' "$old_proto_file";
    } > "$target"
done

echo "Please update ./opentelemetry-proto/README.rst to include the updated version."
