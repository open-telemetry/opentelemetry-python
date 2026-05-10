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
onshutdown()
{
    # send a sigint, to ensure
    # it is caught as a KeyboardInterrupt in the
    # example service.
    kill $EXAMPLE_SERVER_PID
}
trap onshutdown EXIT
# Wait for the example server to accept connections on 127.0.0.1:5000
# before running the W3C tracecontext tests. A fixed `sleep` raced the
# Flask startup on slow CI runners and produced intermittent connection
# errors (see issue #5104).
wait_for_server() {
    host=127.0.0.1
    port=5000
    deadline=$(( $(date +%s) + 30 ))
    while [ "$(date +%s)" -lt "$deadline" ]; do
        # Bail out early if the server process died.
        if ! kill -0 "$EXAMPLE_SERVER_PID" 2>/dev/null; then
            echo "tracecontext example server exited before becoming ready" >&2
            return 1
        fi
        # Use python so we don't depend on extra tools (nc, curl, etc.).
        if python -c "import socket,sys; s=socket.socket(); s.settimeout(1); sys.exit(0 if s.connect_ex(('$host', $port)) == 0 else 1)" 2>/dev/null; then
            return 0
        fi
        sleep 0.5
    done
    echo "tracecontext example server did not become ready within 30s" >&2
    return 1
}
wait_for_server
cd ./target/trace-context/test

# The disabled test is not compatible with an optional part of the W3C 
# spec that we have implemented (dropping duplicated keys from tracestate).
# W3C are planning to include flags for optional features in the test suite.
# https://github.com/w3c/trace-context/issues/529
# FIXME: update test to use flags for optional features when available.
export SERVICE_ENDPOINT=http://127.0.0.1:5000/verify-tracecontext
pytest test.py -k "not test_tracestate_duplicated_keys"