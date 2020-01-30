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
  rm -rf dist/*

 for d in opentelemetry-api/ opentelemetry-sdk/ ext/*/ ; do
   (
     cd "$d"
     python3 setup.py --verbose bdist_wheel --dist-dir "$BASEDIR/dist/"
   )
 done
)
