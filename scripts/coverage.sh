#!/bin/bash

set -e

function cov {
    if [ ${TOX_ENV_NAME:0:4} == "py34" ]
    then
        pytest \
            --ignore-glob=*/setup.py \
            --ignore-glob=instrumentation/opentelemetry-instrumentation-opentracing-shim/tests/testbed/* \
            --cov ${1} \
            --cov-append \
            --cov-branch \
            --cov-report='' \
            ${1}
    else
        pytest \
            --ignore-glob=*/setup.py \
            --cov ${1} \
            --cov-append \
            --cov-branch \
            --cov-report='' \
            ${1}
    fi
}

PYTHON_VERSION=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
PYTHON_VERSION_INFO=(${PYTHON_VERSION//./ })

coverage erase

cov opentelemetry-api
cov opentelemetry-sdk
cov exporter/opentelemetry-exporter-datadog
cov instrumentation/opentelemetry-instrumentation-flask
cov instrumentation/opentelemetry-instrumentation-requests
cov exporter/opentelemetry-exporter-jaeger-proto-grpc
cov exporter/opentelemetry-exporter-jaeger-thrift
cov instrumentation/opentelemetry-instrumentation-opentracing-shim
cov util/opentelemetry-util-http
cov exporter/opentelemetry-exporter-zipkin


cov instrumentation/opentelemetry-instrumentation-aiohttp-client
cov instrumentation/opentelemetry-instrumentation-asgi

coverage report --show-missing
coverage xml
