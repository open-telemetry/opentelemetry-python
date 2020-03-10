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

from __future__ import print_function

import grpc

import hello_world_pb2
import hello_world_pb2_grpc
from opencensus.ext.grpc import client_interceptor
from opencensus.ext.stackdriver import trace_exporter as stackdriver_exporter
from opencensus.trace.tracer import Tracer

HOST_PORT = 'localhost:50051'


def main():
    exporter = stackdriver_exporter.StackdriverExporter()
    tracer = Tracer(exporter=exporter)
    tracer_interceptor = client_interceptor.OpenCensusClientInterceptor(
        tracer,
        host_port=HOST_PORT)
    channel = grpc.insecure_channel(HOST_PORT)
    channel = grpc.intercept_channel(channel, tracer_interceptor)
    stub = hello_world_pb2_grpc.GreeterStub(channel)
    response = stub.SayHello(hello_world_pb2.HelloRequest(name='you'))
    print("Message received: " + response.message)


if __name__ == '__main__':
    main()
