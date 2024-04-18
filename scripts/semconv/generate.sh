#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="${SCRIPT_DIR}/../../"

# freeze the spec version to make SemanticAttributes generation reproducible
SEMCONV_VERSION=v1.25.0
OTEL_SEMCONV_GEN_IMG_VERSION=0.24.0
INCUBATING_DIR=_incubating
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

EXCLUDED_NAMESPACES="jvm aspnetcore dotnet signalr ios android"

generate() {
  TEMPLATE=$1
  OUTPUT_FILE=$2
  FILTER=$3
  STABLE_PACKAGE=$4
  docker run --rm \
    -v ${SCRIPT_DIR}/semantic-conventions/model:/source \
    -v ${SCRIPT_DIR}/templates:/templates \
    -v ${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv/:/output \
    otel/semconvgen:$OTEL_SEMCONV_GEN_IMG_VERSION \
    -f /source \
    --continue-on-validation-errors \
    code \
    --template /templates/${TEMPLATE} \
    --output /output/${OUTPUT_FILE} \
    --file-per-group root_namespace \
    -Dfilter=${FILTER} \
    -Dstable_package=${STABLE_PACKAGE} \
    -Dexcluded_namespaces="$EXCLUDED_NAMESPACES"
}

# stable attributes
mkdir -p ${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv/attributes
generate "semantic_attributes.j2" "attributes/{{snake_prefix}}_attributes.py" "is_stable" ""

# all attributes
mkdir -p ${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv/$INCUBATING_DIR/attributes
generate "semantic_attributes.j2" "$INCUBATING_DIR/attributes/{{snake_prefix}}_attributes.py" "any" "opentelemetry.semconv.attributes"

# stable metrics
mkdir -p ${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv/metrics
generate "semantic_metrics.j2" "metrics/{{snake_prefix}}_metrics.py" "is_stable" ""

# all metrics
mkdir -p ${ROOT_DIR}/opentelemetry-semantic-conventions/src/opentelemetry/semconv/$INCUBATING_DIR/metrics
generate "semantic_metrics.j2" "$INCUBATING_DIR/metrics/{{snake_prefix}}_metrics.py" "any" "opentelemetry.semconv.metrics"

cd "$ROOT_DIR"
