#!/usr/bin/env python
# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=import-error

"""The Python implementation of the GRPC helloworld.Greeter client.

Note that you need ``opentelemetry-ext-grpc`` and ``protobuf`` to be installed
to run these examples. To run this script in the context of the example app,
install ``opentelemetry-example-app``::

    pip install -e ext/opentelemetry-ext-grpc/
    pip install -e docs/examples/opentelemetry-example-app

Then run the server in one shell::

    python -m opentelemetry_example_app.grpc.hello_world_server

and the client in another::

    python -m opentelemetry_example_app.grpc.hello_world_client

See also:
https://github.com/grpc/grpc/blob/master/examples/python/helloworld/greeter_client.py
https://github.com/grpc/grpc/blob/v1.16.x/examples/python/interceptors/default_value/greeter_client.py
"""

import logging

import grpc

from opentelemetry import trace
from opentelemetry.ext.grpc import client_interceptor
from opentelemetry.ext.grpc.grpcext import intercept_channel
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleExportSpanProcessor,
)

try:
    # Relative imports should work in the context of the package, e.g.:
    # `python -m opentelemetry_example_app.grpc.hello_world_client`.
    from .gen import helloworld_pb2, helloworld_pb2_grpc
except ImportError:
    # This will fail when running the file as a script, e.g.:
    # `./hello_world_client.py`
    # fall back to importing from the same directory in this case.
    from gen import helloworld_pb2, helloworld_pb2_grpc

trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    SimpleExportSpanProcessor(ConsoleSpanExporter())
)
tracer = trace.get_tracer(__name__)


def run():
    # NOTE(gRPC Python Team): .close() is possible on a channel and should be
    # used in circumstances in which the with statement does not fit the needs
    # of the code.
    with grpc.insecure_channel("localhost:50051") as channel:

        channel = intercept_channel(channel, client_interceptor(tracer))

        stub = helloworld_pb2_grpc.GreeterStub(channel)

        # stub.SayHello is a _InterceptorUnaryUnaryMultiCallable
        response = stub.SayHello(helloworld_pb2.HelloRequest(name="YOU"))

    print("Greeter client received: " + response.message)


if __name__ == "__main__":
    logging.basicConfig()
    run()
