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
import json

from .common_tests import CommonEncoderTestCases
from opentelemetry import trace as trace_api
from opentelemetry.exporter.zipkin.encoder.v2.json import JsonV2Encoder
from opentelemetry.exporter.zipkin.endpoint import Endpoint
from opentelemetry.sdk import trace
from opentelemetry.trace import SpanKind, TraceFlags


class TestV2JsonEncoder(CommonEncoderTestCases.CommonJsonEncoderTest):

    @staticmethod
    def get_encoder(*args, **kwargs) -> JsonV2Encoder:
        return JsonV2Encoder(*args, **kwargs)

    def test_encode(self):
        service_name = "test-service"
        local_endpoint = {"serviceName": service_name}
        span_kind = JsonV2Encoder.SPAN_KIND_MAP[SpanKind.INTERNAL]

        otel_spans = self.get_exhaustive_otel_span_list()
        trace_id = JsonV2Encoder.encode_trace_id(
            otel_spans[0].context.trace_id
        )

        expected_output = [
            {
                "traceId": trace_id,
                "id": JsonV2Encoder.encode_span_id(
                    otel_spans[0].context.span_id
                ),
                "name": otel_spans[0].name,
                "timestamp": otel_spans[0].start_time // 10 ** 3,
                "duration": (otel_spans[0].end_time // 10 ** 3)
                - (otel_spans[0].start_time // 10 ** 3),
                "localEndpoint": local_endpoint,
                "kind": span_kind,
                "tags": {
                    "key_bool": "False",
                    "key_string": "hello_world",
                    "key_float": "111.22",
                    "otel.status_code": "2",
                    "otel.status_description": "Example description",
                },
                "annotations": [
                    {
                        "timestamp": otel_spans[0].events[0].timestamp
                        // 10 ** 3,
                        "value": json.dumps({
                            "event0": {
                                "annotation_bool": True,
                                "annotation_string": "annotation_test",
                                "key_float": 0.3,
                            }
                        }),
                    }
                ],
                "debug": True,
                "parentId": JsonV2Encoder.encode_span_id(
                    otel_spans[0].parent.span_id
                ),
            },
            {
                "traceId": trace_id,
                "id": JsonV2Encoder.encode_span_id(
                    otel_spans[1].context.span_id
                ),
                "name": otel_spans[1].name,
                "timestamp": otel_spans[1].start_time // 10 ** 3,
                "duration": (otel_spans[1].end_time // 10 ** 3)
                - (otel_spans[1].start_time // 10 ** 3),
                "localEndpoint": local_endpoint,
                "kind": span_kind,
                "tags": {
                    "key_resource": "some_resource",
                    "otel.status_code": "1",
                },
                "annotations": None,
                "debug": False,
            },
            {
                "traceId": trace_id,
                "id": JsonV2Encoder.encode_span_id(
                    otel_spans[2].context.span_id
                ),
                "name": otel_spans[2].name,
                "timestamp": otel_spans[2].start_time // 10 ** 3,
                "duration": (otel_spans[2].end_time // 10 ** 3)
                - (otel_spans[2].start_time // 10 ** 3),
                "localEndpoint": local_endpoint,
                "kind": span_kind,
                "tags": {
                    "key_string": "hello_world",
                    "key_resource": "some_resource",
                    "otel.status_code": "1",
                },
                "annotations": None,
                "debug": False,
            },
            {
                "traceId": trace_id,
                "id": JsonV2Encoder.encode_span_id(
                    otel_spans[3].context.span_id
                ),
                "name": otel_spans[3].name,
                "timestamp": otel_spans[3].start_time // 10 ** 3,
                "duration": (otel_spans[3].end_time // 10 ** 3)
                - (otel_spans[3].start_time // 10 ** 3),
                "localEndpoint": local_endpoint,
                "kind": span_kind,
                "tags": {
                    "otel.instrumentation_library.name": "name",
                    "otel.instrumentation_library.version": "version",
                    "otel.status_code": "1",
                },
                "annotations": None,
                "debug": False,
            },
        ]

        self.assertEqual_encoded_spans(
            json.dumps(expected_output),
            JsonV2Encoder(Endpoint(service_name)).encode(otel_spans),
        )

    def test_encode_id_zero_padding(self):
        service_name = "test-service"
        trace_id = 0x0E0C63257DE34C926F9EFCD03927272E
        span_id = 0x04BF92DEEFC58C92
        parent_id = 0x0AAAAAAAAAAAAAAA
        start_time = 683647322 * 10 ** 9  # in ns
        duration = 50 * 10 ** 6
        end_time = start_time + duration

        otel_span = trace._Span(
            name=service_name,
            context=trace_api.SpanContext(
                trace_id,
                span_id,
                is_remote=False,
                trace_flags=TraceFlags(TraceFlags.SAMPLED),
            ),
            parent=trace_api.SpanContext(trace_id, parent_id, is_remote=False),
        )
        otel_span.start(start_time=start_time)
        otel_span.resource = trace.Resource({})
        otel_span.end(end_time=end_time)

        expected_output = [
            {
                "traceId": format(trace_id, "032x"),
                "id": format(span_id, "016x"),
                "name": service_name,
                "timestamp": JsonV2Encoder.nsec_to_usec_round(start_time),
                "duration": JsonV2Encoder.nsec_to_usec_round(duration),
                "localEndpoint": {"serviceName": service_name},
                "kind": JsonV2Encoder.SPAN_KIND_MAP[SpanKind.INTERNAL],
                "tags": {"otel.status_code": "1"},
                "annotations": None,
                "debug": True,
                "parentId": format(parent_id, "016x"),
            }
        ]

        self.assertEqual(
            json.dumps(expected_output),
            JsonV2Encoder(Endpoint(service_name)).encode([otel_span]),
        )

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

        expected_output = [
            {
                "traceId": JsonV2Encoder.encode_trace_id(trace_id),
                "id": JsonV2Encoder.encode_span_id(span_id),
                "name": service_name,
                "timestamp": JsonV2Encoder.nsec_to_usec_round(start_time),
                "duration": JsonV2Encoder.nsec_to_usec_round(duration),
                "localEndpoint": {"serviceName": service_name},
                "kind": JsonV2Encoder.SPAN_KIND_MAP[SpanKind.INTERNAL],
                "tags": {
                    "k1": tag1_value[:max_tag_value_length],
                    "k2": tag2_value[:max_tag_value_length],
                    "otel.status_code": "1",
                },
                "annotations": None,
                "debug": True,
            }
        ]

        self.assertEqual_encoded_spans(
            json.dumps(expected_output),
            JsonV2Encoder(
                Endpoint(service_name), max_tag_value_length
            ).encode([otel_span]),
        )

