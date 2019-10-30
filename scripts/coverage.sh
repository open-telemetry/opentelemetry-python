#!/bin/bash

set -e

function cov {
    pytest ${1} \
        -c pytest-cov.ini \
        --ignore-glob=*/setup.py \
        --cov opentelemetry-api \
        --cov opentelemetry-sdk \
        --cov ext \
        --cov examples \
        --cov-append \
        --cov-branch \
        --cov-report=
}


coverage erase

cov opentelemetry-api
cov opentelemetry-sdk
cov ext/opentelemetry-ext-http-requests
cov ext/opentelemetry-ext-jaeger
cov ext/opentelemetry-ext-opentracing-shim
cov ext/opentelemetry-ext-wsgi
cov examples/opentelemetry-example-app

coverage report
coverage xml
