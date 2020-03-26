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


"""The Python implementation of the gRPC route guide client.

Note that you need ``opentelemetry-ext-grpc`` and ``protobuf`` to be installed
to run these examples. To run this script in the context of the example app,
install ``opentelemetry-example-app``::

    pip install -e ext/opentelemetry-ext-grpc/
    pip install -e docs/examples/opentelemetry-example-app

Then run the server in one shell::

    python -m opentelemetry_example_app.grpc.route_guide_server

and the client in another::

    python -m opentelemetry_example_app.grpc.route_guide_client

See also:
https://github.com/grpc/grpc/tree/master/examples/python/route_guide
"""


import logging
import random

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
    # `python -m opentelemetry_example_app.grpc.route_guide_client`.
    from .gen import route_guide_pb2, route_guide_pb2_grpc
    from . import route_guide_resources
except ImportError:
    # This will fail when running the file as a script, e.g.:
    # `./route_guide_client.py`
    # fall back to importing from the same directory in this case.
    from gen import route_guide_pb2, route_guide_pb2_grpc
    import route_guide_resources

trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    SimpleExportSpanProcessor(ConsoleSpanExporter())
)
tracer = trace.get_tracer(__name__)


def make_route_note(message, latitude, longitude):
    return route_guide_pb2.RouteNote(
        message=message,
        location=route_guide_pb2.Point(latitude=latitude, longitude=longitude),
    )


def guide_get_one_feature(stub, point):
    feature = stub.GetFeature(point)
    if not feature.location:
        print("Server returned incomplete feature")
        return

    if feature.name:
        print("Feature called %s at %s" % (feature.name, feature.location))
    else:
        print("Found no feature at %s" % feature.location)


def guide_get_feature(stub):
    guide_get_one_feature(
        stub, route_guide_pb2.Point(latitude=409146138, longitude=-746188906)
    )
    guide_get_one_feature(stub, route_guide_pb2.Point(latitude=0, longitude=0))


def guide_list_features(stub):
    rectangle = route_guide_pb2.Rectangle(
        lo=route_guide_pb2.Point(latitude=400000000, longitude=-750000000),
        hi=route_guide_pb2.Point(latitude=420000000, longitude=-730000000),
    )
    print("Looking for features between 40, -75 and 42, -73")

    features = stub.ListFeatures(rectangle)

    for feature in features:
        print("Feature called %s at %s" % (feature.name, feature.location))


def generate_route(feature_list):
    for _ in range(0, 10):
        random_feature = feature_list[random.randint(0, len(feature_list) - 1)]
        print("Visiting point %s" % random_feature.location)
        yield random_feature.location


def guide_record_route(stub):
    feature_list = route_guide_resources.read_route_guide_database()

    route_iterator = generate_route(feature_list)
    route_summary = stub.RecordRoute(route_iterator)
    print("Finished trip with %s points " % route_summary.point_count)
    print("Passed %s features " % route_summary.feature_count)
    print("Travelled %s meters " % route_summary.distance)
    print("It took %s seconds " % route_summary.elapsed_time)


def generate_messages():
    messages = [
        make_route_note("First message", 0, 0),
        make_route_note("Second message", 0, 1),
        make_route_note("Third message", 1, 0),
        make_route_note("Fourth message", 0, 0),
        make_route_note("Fifth message", 1, 0),
    ]
    for msg in messages:
        print("Sending %s at %s" % (msg.message, msg.location))
        yield msg


def guide_route_chat(stub):
    responses = stub.RouteChat(generate_messages())
    for response in responses:
        print(
            "Received message %s at %s" % (response.message, response.location)
        )


def run():

    # NOTE(gRPC Python Team): .close() is possible on a channel and should be
    # used in circumstances in which the with statement does not fit the needs
    # of the code.
    with grpc.insecure_channel("localhost:50051") as channel:
        channel = intercept_channel(channel, client_interceptor(tracer))

        stub = route_guide_pb2_grpc.RouteGuideStub(channel)

        # Unary
        print("-------------- GetFeature --------------")
        guide_get_feature(stub)

        # Server streaming
        print("-------------- ListFeatures --------------")
        guide_list_features(stub)

        # Client streaming
        print("-------------- RecordRoute --------------")
        guide_record_route(stub)

        # Bidirectional streaming
        print("-------------- RouteChat --------------")
        guide_route_chat(stub)


if __name__ == "__main__":
    logging.basicConfig()
    run()
