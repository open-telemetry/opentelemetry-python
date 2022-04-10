#!/bin/bash
# this script generates the documentation required for
# opentelemetry.io

pip install -r requirements/docs.txt

pip install -e opentelemetry-api
pip install -e opentelemetry-semantic-conventions
pip install -e opentelemetry-sdk

TMP_DIR=/tmp/python_otel_docs
rm -Rf ${TMP_DIR}

sphinx-build -M jekyll ./docs ${TMP_DIR}
