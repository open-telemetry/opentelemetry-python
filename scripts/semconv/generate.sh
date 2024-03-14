#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="${SCRIPT_DIR}/../../"

# freeze the spec version to make SemanticAttributes generation reproducible
SPEC_VERSION=v1.21.0
SCHEMA_URL=https://opentelemetry.io/schemas/$SPEC_VERSION
OTEL_SEMCONV_GEN_IMG_VERSION=0.21.0

cd ${SCRIPT_DIR}

rm -rf semantic-conventions || true
mkdir semantic-conventions
cd semantic-conventions

git init
git remote add origin https://github.com/open-telemetry/semantic-conventions.git
git fetch origin "$SPEC_VERSION"
git reset --hard FETCH_HEAD
cd ${SCRIPT_DIR}

docker run --rm \
  -v ${SCRIPT_DIR}/semantic-conventions/model:/source \
  -v ${SCRIPT_DIR}/templates:/templates \
  -v ${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv/trace/:/output \
  otel/semconvgen:$OTEL_SEMCONV_GEN_IMG_VERSION \
  --only span,event,attribute_group \
  -f /source code \
  --template /templates/semantic_attributes.j2 \
  --output /output/__init__.py \
  -Dclass=SpanAttributes \
  -DschemaUrl=$SCHEMA_URL

docker run --rm \
  -v ${SCRIPT_DIR}/semantic-conventions/model:/source \
  -v ${SCRIPT_DIR}/templates:/templates \
  -v ${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv/resource/:/output \
  otel/semconvgen:$OTEL_SEMCONV_GEN_IMG_VERSION \
  --only resource \
  -f /source code \
  --template /templates/semantic_attributes.j2 \
  --output /output/__init__.py \
  -Dclass=ResourceAttributes \
  -DschemaUrl=$SCHEMA_URL

docker run --rm \
  -v ${SCRIPT_DIR}/semantic-conventions/model:/source \
  -v ${SCRIPT_DIR}/templates:/templates \
  -v ${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv/metrics/:/output \
  otel/semconvgen:$OTEL_SEMCONV_GEN_IMG_VERSION \
  --only metric \
  -f /source code \
  --template /templates/semantic_metrics.j2 \
  --output /output/__init__.py \
  -Dclass=MetricInstruments \
  -DschemaUrl=$SCHEMA_URL

cd "$ROOT_DIR"
