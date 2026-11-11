#!/bin/sh

# This script builds wheels for the API, SDK, and extension packages in the
# dist/ dir, to be uploaded to PyPI.

set -ev

BASEDIR=$(dirname "$(readlink -f "$(dirname "$0")")")
DISTDIR=dist

(
  cd "$BASEDIR"

  # Ensure no untracked or modified files exist in the checkout before building
  if [ -n "$(git status --porcelain)" ]; then
    echo "Error! Working tree is dirty before build:"
    git status --porcelain
    exit 1
  fi

  mkdir -p "$DISTDIR"
  rm -rf "${DISTDIR:?}/"*

  for d in opentelemetry-api/ opentelemetry-configuration/ opentelemetry-sdk/ opentelemetry-proto/ opentelemetry-proto-json/ opentelemetry-semantic-conventions/ exporter/*/ shim/*/ propagator/*/ tests/opentelemetry-test-utils/; do
    (
      echo "building $d"
      cd "$d"
      # Some ext directories (such as docker tests) are not intended to be
      # packaged. Verify the intent by looking for a pyproject.toml.
      if [ -f pyproject.toml ]; then
        uv run --frozen --only-dev uv build --no-build-isolation --out-dir "$BASEDIR/$DISTDIR/"
      fi
    )
  done
)
