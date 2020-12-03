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

from opentelemetry import trace as trace_api
from opentelemetry.exporter.zipkin.encoder.v2.protobuf import ProtobufEncoder
from opentelemetry.exporter.zipkin.encoder.v2.protobuf.gen import zipkin_pb2
from opentelemetry.exporter.zipkin.node_endpoint import NodeEndpoint
from opentelemetry.sdk import trace
from opentelemetry.trace import SpanKind, TraceFlags

from .common_tests import CommonEncoderTestCases


class TestProtobufEncoder(CommonEncoderTestCases.CommonEncoderTest):
    @staticmethod
    def get_encoder(*args, **kwargs) -> ProtobufEncoder:
        return ProtobufEncoder(*args, **kwargs)

    def test_encode_trace_id(self):
        for trace_id in (1, 1024, 2 ** 32, 2 ** 64, 2 ** 127):
            self.assertEqual(
                self.get_encoder_default()._encode_trace_id(trace_id),
                trace_id.to_bytes(length=16, byteorder="big", signed=False),
            )

    def test_encode_span_id(self):
        for span_id in (1, 1024, 2 ** 8, 2 ** 16, 2 ** 32, 2 ** 63):
            self.assertEqual(
                self.get_encoder_default()._encode_span_id(span_id),
                span_id.to_bytes(length=8, byteorder="big", signed=False),
            )

    def test_encode_local_endpoint_default(self):
        service_name = "test-service-name"
        self.assertEqual(
            ProtobufEncoder()._encode_local_endpoint(
                NodeEndpoint(service_name)
            ),
            zipkin_pb2.Endpoint(service_name=service_name),
        )

    def test_encode_local_endpoint_explicits(self):
        service_name = "test-service-name"
        ipv4 = "192.168.0.1"
        ipv6 = "2001:db8::c001"
        port = 414120
        self.assertEqual(
            ProtobufEncoder()._encode_local_endpoint(
                NodeEndpoint(service_name, ipv4, ipv6, port)
            ),
            zipkin_pb2.Endpoint(
                service_name=service_name,
                ipv4=ipaddress.ip_address(ipv4).packed,
                ipv6=ipaddress.ip_address(ipv6).packed,
                port=port,
            ),
        )

    def test_encode(self):
        service_name = "test-service"
        local_endpoint = zipkin_pb2.Endpoint(service_name=service_name)
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
                        "key_bool": "False",
                        "key_string": "hello_world",
                        "key_float": "111.22",
                        "otel.status_code": "2",
                        "otel.status_description": "Example description",
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
                                }
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
                        "otel.status_code": "1",
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
                        "otel.status_code": "1",
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
                        "otel.instrumentation_library.name": "name",
                        "otel.instrumentation_library.version": "version",
                        "otel.status_code": "1",
                    },
                    debug=False,
                ),
            ],
        )

        actual_output = zipkin_pb2.ListOfSpans.FromString(
            ProtobufEncoder().serialize(otel_spans, NodeEndpoint(service_name))
        )

        self.assertEqual(actual_output, expected_output)

    def _test_encode_max_tag_length(self, max_tag_value_length: int):
        service_name = "test-service"
        trace_id = 0x0E0C63257DE34C926F9EFCD03927272E
        span_id = 0x04BF92DEEFC58C92
        start_time = 683647322 * 10 ** 9  # in ns
        duration = 50 * 10 ** 6
        end_time = start_time + duration
        tag1_value = "v" * 500
        tag2_value = "v" * 50

        otel_span = trace._Span(
            name=service_name,
            context=trace_api.SpanContext(
                trace_id,
                span_id,
                is_remote=False,
                trace_flags=TraceFlags(TraceFlags.SAMPLED),
            ),
        )
        otel_span.start(start_time=start_time)
        otel_span.resource = trace.Resource({})
        otel_span.set_attribute("k1", tag1_value)
        otel_span.set_attribute("k2", tag2_value)
        otel_span.end(end_time=end_time)

        expected_output = zipkin_pb2.ListOfSpans(
            spans=[
                zipkin_pb2.Span(
                    trace_id=ProtobufEncoder._encode_trace_id(trace_id),
                    id=ProtobufEncoder._encode_span_id(span_id),
                    name=service_name,
                    timestamp=ProtobufEncoder._nsec_to_usec_round(start_time),
                    duration=ProtobufEncoder._nsec_to_usec_round(duration),
                    local_endpoint=zipkin_pb2.Endpoint(
                        service_name=service_name
                    ),
                    kind=ProtobufEncoder.SPAN_KIND_MAP[SpanKind.INTERNAL],
                    tags={
                        "k1": tag1_value[:max_tag_value_length],
                        "k2": tag2_value[:max_tag_value_length],
                        "otel.status_code": "1",
                    },
                    annotations=None,
                    debug=True,
                )
            ]
        )

        actual_output = zipkin_pb2.ListOfSpans.FromString(
            ProtobufEncoder(max_tag_value_length).serialize(
                [otel_span], NodeEndpoint(service_name)
            )
        )

        self.assertEqual(actual_output, expected_output)
