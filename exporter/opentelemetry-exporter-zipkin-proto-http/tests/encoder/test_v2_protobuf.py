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
import ipaddress
import json

from opentelemetry.exporter.zipkin.encoder import (
    _SCOPE_NAME_KEY,
    _SCOPE_VERSION_KEY,
    NAME_KEY,
    VERSION_KEY,
)
from opentelemetry.exporter.zipkin.node_endpoint import NodeEndpoint
from opentelemetry.exporter.zipkin.proto.http.v2 import ProtobufEncoder
from opentelemetry.exporter.zipkin.proto.http.v2.gen import zipkin_pb2
from opentelemetry.test.spantestutil import (
    get_span_with_dropped_attributes_events_links,
)
from opentelemetry.trace import SpanKind

from .common_tests import (  # pylint: disable=import-error
    TEST_SERVICE_NAME,
    CommonEncoderTestCases,
)


# pylint: disable=protected-access
class TestProtobufEncoder(CommonEncoderTestCases.CommonEncoderTest):
    @staticmethod
    def get_encoder(*args, **kwargs) -> ProtobufEncoder:
        return ProtobufEncoder(*args, **kwargs)

    def test_encode_trace_id(self):
        for trace_id in (1, 1024, 2**32, 2**64, 2**127):
            self.assertEqual(
                self.get_encoder_default()._encode_trace_id(trace_id),
                trace_id.to_bytes(length=16, byteorder="big", signed=False),
            )

    def test_encode_span_id(self):
        for span_id in (1, 1024, 2**8, 2**16, 2**32, 2**63):
            self.assertEqual(
                self.get_encoder_default()._encode_span_id(span_id),
                span_id.to_bytes(length=8, byteorder="big", signed=False),
            )

    def test_encode_local_endpoint_default(self):
        self.assertEqual(
            ProtobufEncoder()._encode_local_endpoint(NodeEndpoint()),
            zipkin_pb2.Endpoint(service_name=TEST_SERVICE_NAME),
        )

    def test_encode_local_endpoint_explicits(self):
        ipv4 = "192.168.0.1"
        ipv6 = "2001:db8::c001"
        port = 414120
        self.assertEqual(
            ProtobufEncoder()._encode_local_endpoint(
                NodeEndpoint(ipv4, ipv6, port)
            ),
            zipkin_pb2.Endpoint(
                service_name=TEST_SERVICE_NAME,
                ipv4=ipaddress.ip_address(ipv4).packed,
                ipv6=ipaddress.ip_address(ipv6).packed,
                port=port,
            ),
        )

    def test_encode(self):
        local_endpoint = zipkin_pb2.Endpoint(service_name=TEST_SERVICE_NAME)
        span_kind = ProtobufEncoder.SPAN_KIND_MAP[SpanKind.INTERNAL]

        otel_spans = self.get_exhaustive_otel_span_list()
        trace_id = ProtobufEncoder._encode_trace_id(
            otel_spans[0].context.trace_id
        )
        expected_output = zipkin_pb2.ListOfSpans(
            spans=[
                zipkin_pb2.Span(
                    trace_id=trace_id,
                    id=ProtobufEncoder._encode_span_id(
                        otel_spans[0].context.span_id
                    ),
                    name=otel_spans[0].name,
                    timestamp=ProtobufEncoder._nsec_to_usec_round(
                        otel_spans[0].start_time
                    ),
                    duration=(
                        ProtobufEncoder._nsec_to_usec_round(
                            otel_spans[0].end_time - otel_spans[0].start_time
                        )
                    ),
                    local_endpoint=local_endpoint,
                    kind=span_kind,
                    tags={
                        "key_bool": "false",
                        "key_string": "hello_world",
                        "key_float": "111.22",
                        "otel.status_code": "OK",
                    },
                    debug=True,
                    parent_id=ProtobufEncoder._encode_span_id(
                        otel_spans[0].parent.span_id
                    ),
                    annotations=[
                        zipkin_pb2.Annotation(
                            timestamp=ProtobufEncoder._nsec_to_usec_round(
                                otel_spans[0].events[0].timestamp
                            ),
                            value=json.dumps(
                                {
                                    "event0": {
                                        "annotation_bool": True,
                                        "annotation_string": "annotation_test",
                                        "key_float": 0.3,
                                    }
                                },
                                sort_keys=True,
                            ),
                        ),
                    ],
                ),
                zipkin_pb2.Span(
                    trace_id=trace_id,
                    id=ProtobufEncoder._encode_span_id(
                        otel_spans[1].context.span_id
                    ),
                    name=otel_spans[1].name,
                    timestamp=ProtobufEncoder._nsec_to_usec_round(
                        otel_spans[1].start_time
                    ),
                    duration=(
                        ProtobufEncoder._nsec_to_usec_round(
                            otel_spans[1].end_time - otel_spans[1].start_time
                        )
                    ),
                    local_endpoint=local_endpoint,
                    kind=span_kind,
                    tags={
                        "key_resource": "some_resource",
                        "otel.status_code": "ERROR",
                        "error": "Example description",
                    },
                    debug=False,
                ),
                zipkin_pb2.Span(
                    trace_id=trace_id,
                    id=ProtobufEncoder._encode_span_id(
                        otel_spans[2].context.span_id
                    ),
                    name=otel_spans[2].name,
                    timestamp=ProtobufEncoder._nsec_to_usec_round(
                        otel_spans[2].start_time
                    ),
                    duration=(
                        ProtobufEncoder._nsec_to_usec_round(
                            otel_spans[2].end_time - otel_spans[2].start_time
                        )
                    ),
                    local_endpoint=local_endpoint,
                    kind=span_kind,
                    tags={
                        "key_string": "hello_world",
                        "key_resource": "some_resource",
                    },
                    debug=False,
                ),
                zipkin_pb2.Span(
                    trace_id=trace_id,
                    id=ProtobufEncoder._encode_span_id(
                        otel_spans[3].context.span_id
                    ),
                    name=otel_spans[3].name,
                    timestamp=ProtobufEncoder._nsec_to_usec_round(
                        otel_spans[3].start_time
                    ),
                    duration=(
                        ProtobufEncoder._nsec_to_usec_round(
                            otel_spans[3].end_time - otel_spans[3].start_time
                        )
                    ),
                    local_endpoint=local_endpoint,
                    kind=span_kind,
                    tags={
                        NAME_KEY: "name",
                        VERSION_KEY: "version",
                        _SCOPE_NAME_KEY: "name",
                        _SCOPE_VERSION_KEY: "version",
                    },
                    debug=False,
                ),
            ],
        )

        actual_output = zipkin_pb2.ListOfSpans.FromString(
            ProtobufEncoder().serialize(otel_spans, NodeEndpoint())
        )

        self.assertEqual(actual_output, expected_output)

    def _test_encode_max_tag_length(self, max_tag_value_length: int):
        otel_span, expected_tag_output = self.get_data_for_max_tag_length_test(
            max_tag_value_length
        )
        service_name = otel_span.name

        expected_output = zipkin_pb2.ListOfSpans(
            spans=[
                zipkin_pb2.Span(
                    trace_id=ProtobufEncoder._encode_trace_id(
                        otel_span.context.trace_id
                    ),
                    id=ProtobufEncoder._encode_span_id(
                        otel_span.context.span_id
                    ),
                    name=service_name,
                    timestamp=ProtobufEncoder._nsec_to_usec_round(
                        otel_span.start_time
                    ),
                    duration=ProtobufEncoder._nsec_to_usec_round(
                        otel_span.end_time - otel_span.start_time
                    ),
                    local_endpoint=zipkin_pb2.Endpoint(
                        service_name=service_name
                    ),
                    kind=ProtobufEncoder.SPAN_KIND_MAP[SpanKind.INTERNAL],
                    tags=expected_tag_output,
                    annotations=None,
                    debug=True,
                )
            ]
        )

        actual_output = zipkin_pb2.ListOfSpans.FromString(
            ProtobufEncoder(max_tag_value_length).serialize(
                [otel_span], NodeEndpoint()
            )
        )

        self.assertEqual(actual_output, expected_output)

    def test_dropped_span_attributes(self):
        otel_span = get_span_with_dropped_attributes_events_links()
        # pylint: disable=no-member
        tags = (
            ProtobufEncoder()
            ._encode_span(otel_span, zipkin_pb2.Endpoint())
            .tags
        )

        self.assertEqual("1", tags["otel.dropped_links_count"])
        self.assertEqual("2", tags["otel.dropped_attributes_count"])
        self.assertEqual("3", tags["otel.dropped_events_count"])
