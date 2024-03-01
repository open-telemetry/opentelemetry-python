#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="${SCRIPT_DIR}/../../"

# freeze the spec version to make SemanticAttributes generation reproducible
SEMCONV_VERSION=v1.24.0
OTEL_SEMCONV_GEN_IMG_VERSION=feature-codegen-by-namespace
EXPERIMENTAL_DIR=experimental
cd ${SCRIPT_DIR}

rm -rf semantic-conventions || true
mkdir semantic-conventions
cd semantic-conventions

git init
git remote add origin https://github.com/open-telemetry/semantic-conventions.git
git fetch origin "$SEMCONV_VERSION"
git reset --hard FETCH_HEAD
cd ${SCRIPT_DIR}

# Check new schema version was added to schemas.py manually
SCHEMAS_PY_PATH=${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv/schemas.py
CURRENT_SCHEMAS=$(cat $SCHEMAS_PY_PATH)

if ! grep -q $SEMCONV_VERSION "$SCHEMAS_PY_PATH"; then
  echo "Error: schema version $SEMCONV_VERSION is not found in $SCHEMAS_PY_PATH. Please add it manually."
  exit 1
fi

# stable attributes
docker run --rm \
  -v ${SCRIPT_DIR}/semantic-conventions/model:/source \
  -v ${SCRIPT_DIR}/templates:/templates \
  -v ${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv/:/output \
  otel/semconvgen:$OTEL_SEMCONV_GEN_IMG_VERSION \
  -f /source \
  --strict-validation false \
  code \
  --template /templates/semantic_attributes.j2 \
  --output /output/{{snake_prefix}}_attributes.py \
  --file-per-group root_namespace \
  -Dfilter=is_stable

# experimental attributes and metrics
mkdir -p ${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv/$EXPERIMENTAL_DIR
docker run --rm \
  -v ${SCRIPT_DIR}/semantic-conventions/model:/source \
  -v ${SCRIPT_DIR}/templates:/templates \
  -v ${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv/:/output \
  otel/semconvgen:$OTEL_SEMCONV_GEN_IMG_VERSION \
  -f /source \
  --strict-validation false \
  code \
  --template /templates/semantic_attributes.j2 \
  --output /output/$EXPERIMENTAL_DIR/{{snake_prefix}}_attributes.py \
  --file-per-group root_namespace \
  -Dfilter=is_experimental

# experimental metrics
docker run --rm \
  -v ${SCRIPT_DIR}/semantic-conventions/model:/source \
  -v ${SCRIPT_DIR}/templates:/templates \
  -v ${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv/:/output \
  otel/semconvgen:$OTEL_SEMCONV_GEN_IMG_VERSION \
  -f /source \
  --strict-validation false \
  code \
  --template /templates/semantic_metrics.j2 \
  --output /output/$EXPERIMENTAL_DIR/{{snake_prefix}}_metrics.py \
  --file-per-group root_namespace \
  -Dfilter=is_experimental

cd "$ROOT_DIR"
