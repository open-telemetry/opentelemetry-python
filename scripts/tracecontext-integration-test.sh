#!/bin/sh
set -e 
# hard-coding the git tag to ensure stable builds.
TRACECONTEXT_GIT_TAG="d782773b2cf2fa4afd6a80a93b289d8a74ca894d"
# clone w3c tracecontext tests
mkdir -p target
rm -rf ./target/trace-context
git clone https://github.com/w3c/trace-context ./target/trace-context
cd ./target/trace-context && git checkout $TRACECONTEXT_GIT_TAG && cd -
# start example opentelemetry service, which propagates trace-context by 
# default.
python ./tests/w3c_tracecontext_validation_server.py 1>&2 &
EXAMPLE_SERVER_PID=$!
# give the app server a little time to start up. Not adding some sort
# of delay would cause many of the tracecontext tests to fail being
# unable to connect.
sleep 1
onshutdown() 
{
    # send a sigint, to ensure
    # it is caught as a KeyboardInterrupt in the
    # example service.
    kill $EXAMPLE_SERVER_PID
}
trap onshutdown EXIT
cd ./target/trace-context/test

# The disabled test is not compatible with an optional part of the W3C 
# spec that we have implemented (dropping duplicated keys from tracestate).
# W3C are planning to include flags for optional features in the test suite.
# https://github.com/w3c/trace-context/issues/529
# FIXME: update test to use flags for optional features when available.
export SERVICE_ENDPOINT=http://127.0.0.1:5000/verify-tracecontext
pytest test.py -k "not test_tracestate_duplicated_keys"