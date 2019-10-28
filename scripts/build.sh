#!/bin/sh

# This script builds wheels for the API, SDK, and extension packages in the
# dist/ dir, to be uploaded to PyPI.

set -ev

# Get the latest versions of packaging tools
python3 -m pip install --upgrade pip setuptools wheel

BASEDIR=$(dirname $(readlink -f $(dirname $0)))

(
  cd $BASEDIR
  mkdir -p dist

  # Clean old artifacts
  rm -rf dist/*

  # Clean old artifacts
  for d in opentelemetry-api/ opentelemetry-sdk/ ext/*/ ; do
    (
      cd "$d"
      echo "pwd"
      echo $(pwd)
      python3 setup.py bdist_wheel --dist-dir "$BASEDIR/dist/"
    )
  done
  echo "built packages: "
  ls -lah "$BASEDIR/dist/"
)
