#!/bin/sh

# This script builds wheels for the API, SDK, and extension packages in the
# dist/ dir, to be uploaded to PyPI.

# set -ev

# Ensure that we have the latest versions of Twine, Wheel, and Setuptools.
python3 -m pip install --upgrade pip
python3 -m pip install --upgrade twine wheel setuptools

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
