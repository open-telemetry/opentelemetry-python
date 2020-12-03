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
import abc
import json
import sys
import unittest
from typing import List

from opentelemetry import trace as trace_api
from opentelemetry.exporter.zipkin.encoder import (
    DEFAULT_MAX_TAG_VALUE_LENGTH,
    Encoder,
)
from opentelemetry.exporter.zipkin.node_endpoint import NodeEndpoint
from opentelemetry.sdk import trace
from opentelemetry.sdk.util.instrumentation import InstrumentationInfo
from opentelemetry.trace import TraceFlags
from opentelemetry.trace.status import Status, StatusCode


# pylint: disable=protected-access
class CommonEncoderTestCases:
    class CommonEncoderTest(unittest.TestCase):
        @staticmethod
        @abc.abstractmethod
        def get_encoder(*args, **kwargs) -> Encoder:
            pass

        @classmethod
        def get_encoder_default(cls) -> Encoder:
            return cls.get_encoder()

        @abc.abstractmethod
        def test_encode_trace_id(self):
            pass

        @abc.abstractmethod
        def test_encode_span_id(self):
            pass

        @abc.abstractmethod
        def test_encode_local_endpoint_default(self):
            pass

        @abc.abstractmethod
        def test_encode_local_endpoint_explicits(self):
            pass

        @abc.abstractmethod
        def _test_encode_max_tag_length(self, max_tag_value_length: int):
            pass

        def test_encode_max_tag_length_128(self):
            self._test_encode_max_tag_length(128)

        def test_encode_max_tag_length_2(self):
            self._test_encode_max_tag_length(2)

        def test_constructor_default(self):
            encoder = self.get_encoder()

            self.assertEqual(
                DEFAULT_MAX_TAG_VALUE_LENGTH, encoder.max_tag_value_length
            )

        def test_constructor_max_tag_value_length(self):
            max_tag_value_length = 123456
            encoder = self.get_encoder(max_tag_value_length)
            self.assertEqual(
                max_tag_value_length, encoder.max_tag_value_length
            )

        def test_nsec_to_usec_round(self):
            base_time_nsec = 683647322 * 10 ** 9
            for nsec in (
                base_time_nsec,
                base_time_nsec + 150 * 10 ** 6,
                base_time_nsec + 300 * 10 ** 6,
                base_time_nsec + 400 * 10 ** 6,
            ):
                self.assertEqual(
                    (nsec + 500) // 10 ** 3,
                    self.get_encoder_default()._nsec_to_usec_round(nsec),
                )

        def test_encode_debug(self):
            self.assertFalse(
                self.get_encoder_default()._encode_debug(
                    trace_api.SpanContext(
                        trace_id=0x000000000000000000000000DEADBEEF,
                        span_id=0x00000000DEADBEF0,
                        is_remote=False,
                        trace_flags=TraceFlags(TraceFlags.DEFAULT),
                    )
                )
            )
            self.assertTrue(
                self.get_encoder_default()._encode_debug(
                    trace_api.SpanContext(
                        trace_id=0x000000000000000000000000DEADBEEF,
                        span_id=0x00000000DEADBEF0,
                        is_remote=False,
                        trace_flags=TraceFlags(TraceFlags.SAMPLED),
                    )
                )
            )

        def test_get_parent_id_from_span(self):
            parent_id = 0x00000000DEADBEF0
            self.assertEqual(
                parent_id,
                self.get_encoder_default()._get_parent_id(
                    trace._Span(
                        name="test-span",
                        context=trace_api.SpanContext(
                            0x000000000000000000000000DEADBEEF,
                            0x04BF92DEEFC58C92,
                            is_remote=False,
                        ),
                        parent=trace_api.SpanContext(
                            0x0000000000000000000000AADEADBEEF,
                            parent_id,
                            is_remote=False,
                        ),
                    )
                ),
            )

        def test_get_parent_id_from_span_context(self):
            parent_id = 0x00000000DEADBEF0
            self.assertEqual(
                parent_id,
                self.get_encoder_default()._get_parent_id(
                    trace_api.SpanContext(
                        trace_id=0x000000000000000000000000DEADBEEF,
                        span_id=parent_id,
                        is_remote=False,
                    ),
                ),
            )

        @staticmethod
        def get_exhaustive_otel_span_list() -> List[trace._Span]:
            trace_id = 0x6E0C63257DE34C926F9EFCD03927272E

            base_time = 683647322 * 10 ** 9  # in ns
            start_times = (
                base_time,
                base_time + 150 * 10 ** 6,
                base_time + 300 * 10 ** 6,
                base_time + 400 * 10 ** 6,
            )
            end_times = (
                start_times[0] + (50 * 10 ** 6),
                start_times[1] + (100 * 10 ** 6),
                start_times[2] + (200 * 10 ** 6),
                start_times[3] + (300 * 10 ** 6),
            )

            parent_span_context = trace_api.SpanContext(
                trace_id, 0x1111111111111111, is_remote=False
            )

            other_context = trace_api.SpanContext(
                trace_id, 0x2222222222222222, is_remote=False
            )

            span1 = trace._Span(
                name="test-span-1",
                context=trace_api.SpanContext(
                    trace_id,
                    0x34BF92DEEFC58C92,
                    is_remote=False,
                    trace_flags=TraceFlags(TraceFlags.SAMPLED),
                ),
                parent=parent_span_context,
                events=(
                    trace.Event(
                        name="event0",
                        timestamp=base_time + 50 * 10 ** 6,
                        attributes={
                            "annotation_bool": True,
                            "annotation_string": "annotation_test",
                            "key_float": 0.3,
                        },
                    ),
                ),
                links=(
                    trace_api.Link(
                        context=other_context, attributes={"key_bool": True}
                    ),
                ),
            )
            span1.start(start_time=start_times[0])
            span1.resource = trace.Resource({})
            # added here to preserve order
            span1.set_attribute("key_bool", False)
            span1.set_attribute("key_string", "hello_world")
            span1.set_attribute("key_float", 111.22)
            span1.set_status(Status(StatusCode.ERROR, "Example description"))
            span1.end(end_time=end_times[0])

            span2 = trace._Span(
                name="test-span-2", context=parent_span_context, parent=None
            )
            span2.start(start_time=start_times[1])
            span2.resource = trace.Resource(
                attributes={"key_resource": "some_resource"}
            )
            span2.end(end_time=end_times[1])

            span3 = trace._Span(
                name="test-span-3", context=other_context, parent=None
            )
            span3.start(start_time=start_times[2])
            span3.set_attribute("key_string", "hello_world")
            span3.resource = trace.Resource(
                attributes={"key_resource": "some_resource"}
            )
            span3.end(end_time=end_times[2])

            span4 = trace._Span(
                name="test-span-3", context=other_context, parent=None
            )
            span4.start(start_time=start_times[3])
            span4.resource = trace.Resource({})
            span4.end(end_time=end_times[3])
            span4.instrumentation_info = InstrumentationInfo(
                name="name", version="version"
            )

            return [span1, span2, span3, span4]

    # pylint: disable=W0223
    class CommonJsonEncoderTest(CommonEncoderTest, abc.ABC):
        def test_encode_trace_id(self):
            for trace_id in (1, 1024, 2 ** 32, 2 ** 64, 2 ** 65):
                self.assertEqual(
                    format(trace_id, "032x"),
                    self.get_encoder_default()._encode_trace_id(trace_id),
                )

        def test_encode_span_id(self):
            for span_id in (1, 1024, 2 ** 8, 2 ** 16, 2 ** 32, 2 ** 64):
                self.assertEqual(
                    format(span_id, "016x"),
                    self.get_encoder_default()._encode_span_id(span_id),
                )

        def test_encode_local_endpoint_default(self):
            service_name = "test-service-name"
            self.assertEqual(
                self.get_encoder_default()._encode_local_endpoint(
                    NodeEndpoint(service_name)
                ),
                {"serviceName": service_name},
            )

        def test_encode_local_endpoint_explicits(self):
            service_name = "test-service-name"
            ipv4 = "192.168.0.1"
            ipv6 = "2001:db8::c001"
            port = 414120
            self.assertEqual(
                self.get_encoder_default()._encode_local_endpoint(
                    NodeEndpoint(service_name, ipv4, ipv6, port)
                ),
                {
                    "serviceName": service_name,
                    "ipv4": ipv4,
                    "ipv6": ipv6,
                    "port": port,
                },
            )

        @staticmethod
        def pop_and_sort(source_list, source_index, sort_key):
            """
            Convenience method that will pop a specified index from a list,
            sort it by a given key and then return it.
            """
            popped_item = source_list.pop(source_index, None)
            if popped_item is not None:
                popped_item = sorted(popped_item, key=lambda x: x[sort_key])
            return popped_item

        def assert_equal_encoded_spans(self, expected_spans, actual_spans):
            if sys.version_info.major == 3 and sys.version_info.minor <= 5:
                expected_spans = json.loads(expected_spans)
                actual_spans = json.loads(actual_spans)
                for expected_span, actual_span in zip(
                    expected_spans, actual_spans
                ):
                    actual_annotations = self.pop_and_sort(
                        actual_span, "annotations", "timestamp"
                    )
                    expected_annotations = self.pop_and_sort(
                        expected_span, "annotations", "timestamp"
                    )
                    expected_binary_annotations = self.pop_and_sort(
                        expected_span, "binaryAnnotations", "key"
                    )
                    actual_binary_annotations = self.pop_and_sort(
                        actual_span, "binaryAnnotations", "key"
                    )
                    self.assertEqual(actual_span, expected_span)
                    self.assertEqual(actual_annotations, expected_annotations)
                    self.assertEqual(
                        actual_binary_annotations, expected_binary_annotations
                    )
            else:
                self.assertEqual(expected_spans, actual_spans)
