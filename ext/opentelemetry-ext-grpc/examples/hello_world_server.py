#!/usr/bin/env python
# Copyright 2020, OpenTelemetry Authors
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

import helloworld_pb2
import helloworld_pb2_grpc
from opentelemetry.ext.grpc import server_interceptor


class Greeter(helloworld_pb2_grpc.GreeterServicer):

    def SayHello(self, request, context):
        return helloworld_pb2.HelloReply(message='Hello, %s!' % request.name)


def serve():

    interceptor = server_interceptor.OpenTelemetryServerInterceptor()
    # server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10),
                         interceptors=(interceptor,))

    helloworld_pb2_grpc.add_GreeterServicer_to_server(Greeter(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig()
    serve()
