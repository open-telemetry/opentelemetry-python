#!/bin/sh
set -e 
# hard-coding the git tag to ensure stable builds.
TRACECONTEXT_GIT_TAG="98f210efd89c63593dce90e2bae0a1bdcb986f51"
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
function onshutdown {
    # send a sigint, to ensure
    # it is caught as a KeyboardInterrupt in the
    # example service.
    kill $EXAMPLE_SERVER_PID
}
trap onshutdown EXIT
cd ./target/trace-context/test
python test.py http://127.0.0.1:5000/verify-tracecontext