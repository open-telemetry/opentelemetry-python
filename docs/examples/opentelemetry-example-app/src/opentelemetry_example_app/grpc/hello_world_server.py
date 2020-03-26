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

# https://github.com/grpc/grpc/blob/master/examples/python/helloworld/greeter_server.py
"""The Python implementation of the GRPC helloworld.Greeter server."""

import logging
from concurrent import futures

import grpc

from opentelemetry import trace
from opentelemetry.ext.grpc import server_interceptor
from opentelemetry.ext.grpc.grpcext import intercept_server
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleExportSpanProcessor,
)

try:
    # Relative imports should work in the context of the package, e.g.:
    # `python -m opentelemetry_example_app.grpc.hello_world_server`.
    from .gen import helloworld_pb2, helloworld_pb2_grpc
except ImportError:
    # This will fail when running the file as a script, e.g.:
    # `./hello_world_server.py`
    # fall back to importing from the same directory in this case.
    from gen import helloworld_pb2, helloworld_pb2_grpc

trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    SimpleExportSpanProcessor(ConsoleSpanExporter())
)
tracer = trace.get_tracer(__name__)


class Greeter(helloworld_pb2_grpc.GreeterServicer):
    def SayHello(self, request, context):
        return helloworld_pb2.HelloReply(message="Hello, %s!" % request.name)


def serve():

    server = grpc.server(futures.ThreadPoolExecutor())
    server = intercept_server(server, server_interceptor(tracer))

    helloworld_pb2_grpc.add_GreeterServicer_to_server(Greeter(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig()
    serve()
