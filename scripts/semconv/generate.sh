#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="${SCRIPT_DIR}/../../"

# freeze the spec version to make SemanticAttributes generation reproducible
SPEC_VERSION=v1.23.1
SPEC_VERSION_ESCAPED=v1_23_1
SCHEMA_URL=https://opentelemetry.io/schemas/$SPEC_VERSION
OTEL_SEMCONV_GEN_IMG_VERSION=foo15

cd ${SCRIPT_DIR}

rm -rf semantic-conventions || true
mkdir semantic-conventions
cd semantic-conventions

git init
git remote add origin https://github.com/open-telemetry/semantic-conventions.git
git fetch origin "$SPEC_VERSION"
git reset --hard FETCH_HEAD
cd ${SCRIPT_DIR}

# stable attributes
docker run --rm \
  -v ${SCRIPT_DIR}/semantic-conventions/model:/source \
  -v ${SCRIPT_DIR}/templates:/templates \
  -v ${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv/:/output \
  semconvgen:$OTEL_SEMCONV_GEN_IMG_VERSION \
  -f /source code \
  --template /templates/semantic_attributes.j2 \
  --output /output/_attributes.py \
  --file-per-group root_namespace \
  -Dfilter=is_stable

mkdir -p ${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv/$SPEC_VERSION_ESCAPED
# experimental attributes
docker run --rm \
  -v ${SCRIPT_DIR}/semantic-conventions/model:/source \
  -v ${SCRIPT_DIR}/templates:/templates \
  -v ${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv/:/output \
  semconvgen:$OTEL_SEMCONV_GEN_IMG_VERSION \
  -f /source code \
  --template /templates/semantic_attributes.j2 \
  --output /output/$SPEC_VERSION_ESCAPED/_attributes.py \
  --file-per-group root_namespace \
  -Dfilter=is_experimental

# experimental metrics
docker run --rm \
  -v ${SCRIPT_DIR}/semantic-conventions/model:/source \
  -v ${SCRIPT_DIR}/templates:/templates \
  -v ${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv/:/output \
  semconvgen:$OTEL_SEMCONV_GEN_IMG_VERSION \
  -f /source code \
  --template /templates/semantic_metrics.j2 \
  --output /output/$SPEC_VERSION_ESCAPED/_metrics.py \
  --file-per-group root_namespace \
  -Dfilter=is_experimental

cd "$ROOT_DIR"
