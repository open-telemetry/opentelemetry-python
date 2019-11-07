#!/bin/bash

set -e

function cov {
    if [ ${TOX_ENV_NAME:0:4} == "py34" ]
    then
        pytest \
            --ignore-glob=*/setup.py \
            --ignore-glob=ext/opentelemetry-ext-opentracing-shim/tests/testbed/* \
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


coverage erase

cov opentelemetry-api
cov opentelemetry-sdk
cov ext/opentelemetry-ext-flask
cov ext/opentelemetry-ext-http-requests
cov ext/opentelemetry-ext-jaeger
cov ext/opentelemetry-ext-opentracing-shim
cov ext/opentelemetry-ext-wsgi
cov ext/opentelemetry-ext-zipkin
cov examples/opentelemetry-example-app

coverage report
coverage xml
