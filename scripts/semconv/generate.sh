#!/bin/bash
set -ex

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="${SCRIPT_DIR}/../.."

# freeze the spec version to make SemanticAttributes generation reproducible
SEMCONV_VERSION=1.28.0
SEMCONV_VERSION_TAG=v$SEMCONV_VERSION
OTEL_WEAVER_IMG_VERSION=v0.10.0
INCUBATING_DIR=_incubating
cd ${SCRIPT_DIR}

rm -rf semantic-conventions || true
mkdir semantic-conventions
cd semantic-conventions

git init
git remote add origin https://github.com/open-telemetry/semantic-conventions.git
git fetch origin "$SEMCONV_VERSION_TAG"
git reset --hard FETCH_HEAD
cd ${SCRIPT_DIR}

# Check new schema version was added to schemas.py manually
SCHEMAS_PY_PATH=${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv/schemas.py

if ! grep -q $SEMCONV_VERSION "$SCHEMAS_PY_PATH"; then
  echo "Error: schema version $SEMCONV_VERSION is not found in $SCHEMAS_PY_PATH. Please add it manually."
  exit 1
fi

generate() {
  TARGET=$1
  OUTPUT=$2
  FILTER=$3
  docker run --rm \
    -v ${SCRIPT_DIR}/semantic-conventions/model:/source \
    -v ${SCRIPT_DIR}/templates:/templates \
    -v ${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv/:/output \
    otel/weaver:$OTEL_WEAVER_IMG_VERSION \
    registry \
    generate \
    --registry=/source \
    --templates=/templates \
    ${TARGET} \
    /output/${TARGET} \
    --param output=${OUTPUT} \
    --param filter=${FILTER}
}

# stable attributes and metrics
mkdir -p ${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv/attributes
mkdir -p ${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv/metrics
generate "./" "./" "stable"

mkdir -p ${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv/${INCUBATING_DIR}/attributes
mkdir -p ${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv/${INCUBATING_DIR}/metrics
generate "./" "./${INCUBATING_DIR}/" "any"

cd "$ROOT_DIR"
${ROOT_DIR}/.tox/lint/bin/black --config pyproject.toml ${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv
${ROOT_DIR}/.tox/lint/bin/isort ${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv
