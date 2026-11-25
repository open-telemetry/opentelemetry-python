#!/bin/sh

# This script builds wheels for the API, SDK, and extension packages in the
# dist/ dir, to be uploaded to PyPI.

set -ev

BASEDIR=$(dirname "$(readlink -f "$(dirname $0)")")
DISTDIR=dist

# Get the versions of packaging tools recorded in the lockfile
uv sync --locked --only-group build --project "$BASEDIR"
PATH="$BASEDIR/.venv/bin:$PATH"
export PATH

(
  cd $BASEDIR
  mkdir -p $DISTDIR
  rm -rf ${DISTDIR:?}/*

 for d in opentelemetry-api/ opentelemetry-configuration/ opentelemetry-sdk/ opentelemetry-proto/ opentelemetry-proto-json/ opentelemetry-semantic-conventions/ exporter/*/ shim/*/ propagator/*/ tests/opentelemetry-test-utils/; do
   (
     echo "building $d"
     cd "$d"
     # Some ext directories (such as docker tests) are not intended to be
     # packaged. Verify the intent by looking for a pyproject.toml.
     if [ -f pyproject.toml ]; then
      python3 -m build --outdir "$BASEDIR/dist/"
     fi
   )
 done
)
