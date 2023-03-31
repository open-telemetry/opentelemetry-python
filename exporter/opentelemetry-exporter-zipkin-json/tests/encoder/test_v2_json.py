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

from opentelemetry import trace as trace_api
from opentelemetry.exporter.zipkin.encoder import (
    _SCOPE_NAME_KEY,
    _SCOPE_VERSION_KEY,
    NAME_KEY,
    VERSION_KEY,
)
from opentelemetry.exporter.zipkin.json.v2 import JsonV2Encoder
from opentelemetry.exporter.zipkin.node_endpoint import NodeEndpoint
from opentelemetry.sdk import trace
from opentelemetry.test.spantestutil import (
    get_span_with_dropped_attributes_events_links,
)
from opentelemetry.trace import SpanKind, TraceFlags

from .common_tests import (  # pylint: disable=import-error
    TEST_SERVICE_NAME,
    CommonEncoderTestCases,
)


# pylint: disable=protected-access
class TestV2JsonEncoder(CommonEncoderTestCases.CommonJsonEncoderTest):
    @staticmethod
    def get_encoder(*args, **kwargs) -> JsonV2Encoder:
        return JsonV2Encoder(*args, **kwargs)

    def test_encode(self):
        local_endpoint = {"serviceName": TEST_SERVICE_NAME}
        span_kind = JsonV2Encoder.SPAN_KIND_MAP[SpanKind.INTERNAL]

        otel_spans = self.get_exhaustive_otel_span_list()
        trace_id = JsonV2Encoder._encode_trace_id(
            otel_spans[0].context.trace_id
        )

        expected_output = [
            {
                "traceId": trace_id,
                "id": JsonV2Encoder._encode_span_id(
                    otel_spans[0].context.span_id
                ),
                "name": otel_spans[0].name,
                "timestamp": otel_spans[0].start_time // 10**3,
                "duration": (otel_spans[0].end_time // 10**3)
                - (otel_spans[0].start_time // 10**3),
                "localEndpoint": local_endpoint,
                "kind": span_kind,
                "tags": {
                    "key_bool": "false",
                    "key_string": "hello_world",
                    "key_float": "111.22",
                    "otel.status_code": "OK",
                },
                "annotations": [
                    {
                        "timestamp": otel_spans[0].events[0].timestamp
                        // 10**3,
                        "value": json.dumps(
                            {
                                "event0": {
                                    "annotation_bool": True,
                                    "annotation_string": "annotation_test",
                                    "key_float": 0.3,
                                }
                            },
                            sort_keys=True,
                        ),
                    }
                ],
                "debug": True,
                "parentId": JsonV2Encoder._encode_span_id(
                    otel_spans[0].parent.span_id
                ),
            },
            {
                "traceId": trace_id,
                "id": JsonV2Encoder._encode_span_id(
                    otel_spans[1].context.span_id
                ),
                "name": otel_spans[1].name,
                "timestamp": otel_spans[1].start_time // 10**3,
                "duration": (otel_spans[1].end_time // 10**3)
                - (otel_spans[1].start_time // 10**3),
                "localEndpoint": local_endpoint,
                "kind": span_kind,
                "tags": {
                    "key_resource": "some_resource",
                    "otel.status_code": "ERROR",
                    "error": "Example description",
                },
            },
            {
                "traceId": trace_id,
                "id": JsonV2Encoder._encode_span_id(
                    otel_spans[2].context.span_id
                ),
                "name": otel_spans[2].name,
                "timestamp": otel_spans[2].start_time // 10**3,
                "duration": (otel_spans[2].end_time // 10**3)
                - (otel_spans[2].start_time // 10**3),
                "localEndpoint": local_endpoint,
                "kind": span_kind,
                "tags": {
                    "key_string": "hello_world",
                    "key_resource": "some_resource",
                },
            },
            {
                "traceId": trace_id,
                "id": JsonV2Encoder._encode_span_id(
                    otel_spans[3].context.span_id
                ),
                "name": otel_spans[3].name,
                "timestamp": otel_spans[3].start_time // 10**3,
                "duration": (otel_spans[3].end_time // 10**3)
                - (otel_spans[3].start_time // 10**3),
                "localEndpoint": local_endpoint,
                "kind": span_kind,
                "tags": {
                    NAME_KEY: "name",
                    VERSION_KEY: "version",
                    _SCOPE_NAME_KEY: "name",
                    _SCOPE_VERSION_KEY: "version",
                },
            },
        ]

        self.assert_equal_encoded_spans(
            json.dumps(expected_output),
            JsonV2Encoder().serialize(otel_spans, NodeEndpoint()),
        )

    def test_encode_id_zero_padding(self):
        trace_id = 0x0E0C63257DE34C926F9EFCD03927272E
        span_id = 0x04BF92DEEFC58C92
        parent_id = 0x0AAAAAAAAAAAAAAA
        start_time = 683647322 * 10**9  # in ns
        duration = 50 * 10**6
        end_time = start_time + duration

        otel_span = trace._Span(
            name=TEST_SERVICE_NAME,
            context=trace_api.SpanContext(
                trace_id,
                span_id,
                is_remote=False,
                trace_flags=TraceFlags(TraceFlags.SAMPLED),
            ),
            parent=trace_api.SpanContext(trace_id, parent_id, is_remote=False),
            resource=trace.Resource({}),
        )
        otel_span.start(start_time=start_time)
        otel_span.end(end_time=end_time)

        expected_output = [
            {
                "traceId": format(trace_id, "032x"),
                "id": format(span_id, "016x"),
                "name": TEST_SERVICE_NAME,
                "timestamp": JsonV2Encoder._nsec_to_usec_round(start_time),
                "duration": JsonV2Encoder._nsec_to_usec_round(duration),
                "localEndpoint": {"serviceName": TEST_SERVICE_NAME},
                "kind": JsonV2Encoder.SPAN_KIND_MAP[SpanKind.INTERNAL],
                "debug": True,
                "parentId": format(parent_id, "016x"),
            }
        ]

        self.assert_equal_encoded_spans(
            json.dumps(expected_output),
            JsonV2Encoder().serialize([otel_span], NodeEndpoint()),
        )

    def _test_encode_max_tag_length(self, max_tag_value_length: int):
        otel_span, expected_tag_output = self.get_data_for_max_tag_length_test(
            max_tag_value_length
        )
        service_name = otel_span.name

        expected_output = [
            {
                "traceId": JsonV2Encoder._encode_trace_id(
                    otel_span.context.trace_id
                ),
                "id": JsonV2Encoder._encode_span_id(otel_span.context.span_id),
                "name": service_name,
                "timestamp": JsonV2Encoder._nsec_to_usec_round(
                    otel_span.start_time
                ),
                "duration": JsonV2Encoder._nsec_to_usec_round(
                    otel_span.end_time - otel_span.start_time
                ),
                "localEndpoint": {"serviceName": service_name},
                "kind": JsonV2Encoder.SPAN_KIND_MAP[SpanKind.INTERNAL],
                "tags": expected_tag_output,
                "debug": True,
            }
        ]

        self.assert_equal_encoded_spans(
            json.dumps(expected_output),
            JsonV2Encoder(max_tag_value_length).serialize(
                [otel_span], NodeEndpoint()
            ),
        )

    def test_dropped_span_attributes(self):
        otel_span = get_span_with_dropped_attributes_events_links()
        tags = JsonV2Encoder()._encode_span(otel_span, "test")["tags"]

        self.assertEqual("1", tags["otel.dropped_links_count"])
        self.assertEqual("2", tags["otel.dropped_attributes_count"])
        self.assertEqual("3", tags["otel.dropped_events_count"])
