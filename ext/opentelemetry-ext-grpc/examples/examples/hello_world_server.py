# Copyright 2019, OpenTelemetry Authors
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

import time
from concurrent import futures

import grpc

import hello_world_pb2
import hello_world_pb2_grpc
from opencensus.ext.grpc import server_interceptor
from opencensus.ext.stackdriver import trace_exporter as stackdriver_exporter
from opencensus.trace import samplers

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class HelloWorld(hello_world_pb2_grpc.GreeterServicer):

    def SayHello(self, request, context):
        return hello_world_pb2.HelloReply(message='Hello, %s!' % request.name)


def serve():
    sampler = samplers.AlwaysOnSampler()
    exporter = stackdriver_exporter.StackdriverExporter()
    tracer_interceptor = server_interceptor.OpenCensusServerInterceptor(
        sampler, exporter)
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=(tracer_interceptor,))
    hello_world_pb2_grpc.add_GreeterServicer_to_server(HelloWorld(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    serve()
