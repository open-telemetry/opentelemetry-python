#!/bin/sh

# This script builds wheels for the API, SDK, and extension packages in the
# dist/ dir, to be uploaded to PyPI.

set -ev

# Get the latest versions of packaging tools
python3 -m pip install --user --upgrade pip setuptools wheel

BASEDIR=$(dirname $(readlink -f $(dirname $0)))

(
  cd $BASEDIR
  mkdir -p dist
  rm -rf dist/*

 for d in opentelemetry-api/ opentelemetry-sdk/ ext/*/ ; do
   (
     echo "building $d"
     cd "$d"
     # some ext directories (such as docker tests)
     # are not intended to be packaged. Verify the
     # intent by looking for a setup.py
     if [ -f setup.py ]; then
      python3 setup.py --verbose bdist_wheel --dist-dir "$BASEDIR/dist/" sdist --dist-dir "$BASEDIR/dist/"
     fi
   )
 done
)
