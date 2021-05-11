#!/bin/bash
# this script generates the documentation required for
# opentelemetry.io

pip install -r docs-requirements.txt

TMP_DIR=/tmp/website_docs
rm -Rf ${TMP_DIR}

sphinx-build -M jekyll ./docs ${TMP_DIR}
cp ${TMP_DIR}/jekyll/getting-started.md ./website_docs/