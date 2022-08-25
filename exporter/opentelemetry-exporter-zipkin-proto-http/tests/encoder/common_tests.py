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
import unittest
from typing import Dict, List

from opentelemetry import trace as trace_api
from opentelemetry.exporter.zipkin.encoder import (
    DEFAULT_MAX_TAG_VALUE_LENGTH,
    Encoder,
)
from opentelemetry.exporter.zipkin.node_endpoint import NodeEndpoint
from opentelemetry.sdk import trace
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.trace import TraceFlags
from opentelemetry.trace.status import Status, StatusCode

TEST_SERVICE_NAME = "test_service"


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

        def test_encode_max_tag_length_2(self):
            self._test_encode_max_tag_length(2)

        def test_encode_max_tag_length_5(self):
            self._test_encode_max_tag_length(5)

        def test_encode_max_tag_length_9(self):
            self._test_encode_max_tag_length(9)

        def test_encode_max_tag_length_10(self):
            self._test_encode_max_tag_length(10)

        def test_encode_max_tag_length_11(self):
            self._test_encode_max_tag_length(11)

        def test_encode_max_tag_length_128(self):
            self._test_encode_max_tag_length(128)

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
            base_time_nsec = 683647322 * 10**9
            for nsec in (
                base_time_nsec,
                base_time_nsec + 150 * 10**6,
                base_time_nsec + 300 * 10**6,
                base_time_nsec + 400 * 10**6,
            ):
                self.assertEqual(
                    (nsec + 500) // 10**3,
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
        def get_data_for_max_tag_length_test(
            max_tag_length: int,
        ) -> (trace._Span, Dict):
            start_time = 683647322 * 10**9  # in ns
            duration = 50 * 10**6
            end_time = start_time + duration

            span = trace._Span(
                name=TEST_SERVICE_NAME,
                context=trace_api.SpanContext(
                    0x0E0C63257DE34C926F9EFCD03927272E,
                    0x04BF92DEEFC58C92,
                    is_remote=False,
                    trace_flags=TraceFlags(TraceFlags.SAMPLED),
                ),
                resource=trace.Resource({}),
            )
            span.start(start_time=start_time)
            span.set_attribute("string1", "v" * 500)
            span.set_attribute("string2", "v" * 50)
            span.set_attribute("list1", ["a"] * 25)
            span.set_attribute("list2", ["a"] * 10)
            span.set_attribute("list3", [2] * 25)
            span.set_attribute("list4", [2] * 10)
            span.set_attribute("list5", [True] * 25)
            span.set_attribute("list6", [True] * 10)
            span.set_attribute("tuple1", ("a",) * 25)
            span.set_attribute("tuple2", ("a",) * 10)
            span.set_attribute("tuple3", (2,) * 25)
            span.set_attribute("tuple4", (2,) * 10)
            span.set_attribute("tuple5", (True,) * 25)
            span.set_attribute("tuple6", (True,) * 10)
            span.set_attribute("range1", range(0, 25))
            span.set_attribute("range2", range(0, 10))
            span.set_attribute("empty_list", [])
            span.set_attribute("none_list", ["hello", None, "world"])
            span.end(end_time=end_time)

            expected_outputs = {
                2: {
                    "string1": "vv",
                    "string2": "vv",
                    "list1": "[]",
                    "list2": "[]",
                    "list3": "[]",
                    "list4": "[]",
                    "list5": "[]",
                    "list6": "[]",
                    "tuple1": "[]",
                    "tuple2": "[]",
                    "tuple3": "[]",
                    "tuple4": "[]",
                    "tuple5": "[]",
                    "tuple6": "[]",
                    "range1": "[]",
                    "range2": "[]",
                    "empty_list": "[]",
                    "none_list": "[]",
                },
                5: {
                    "string1": "vvvvv",
                    "string2": "vvvvv",
                    "list1": '["a"]',
                    "list2": '["a"]',
                    "list3": '["2"]',
                    "list4": '["2"]',
                    "list5": "[]",
                    "list6": "[]",
                    "tuple1": '["a"]',
                    "tuple2": '["a"]',
                    "tuple3": '["2"]',
                    "tuple4": '["2"]',
                    "tuple5": "[]",
                    "tuple6": "[]",
                    "range1": '["0"]',
                    "range2": '["0"]',
                    "empty_list": "[]",
                    "none_list": "[]",
                },
                9: {
                    "string1": "vvvvvvvvv",
                    "string2": "vvvvvvvvv",
                    "list1": '["a","a"]',
                    "list2": '["a","a"]',
                    "list3": '["2","2"]',
                    "list4": '["2","2"]',
                    "list5": '["true"]',
                    "list6": '["true"]',
                    "tuple1": '["a","a"]',
                    "tuple2": '["a","a"]',
                    "tuple3": '["2","2"]',
                    "tuple4": '["2","2"]',
                    "tuple5": '["true"]',
                    "tuple6": '["true"]',
                    "range1": '["0","1"]',
                    "range2": '["0","1"]',
                    "empty_list": "[]",
                    "none_list": '["hello"]',
                },
                10: {
                    "string1": "vvvvvvvvvv",
                    "string2": "vvvvvvvvvv",
                    "list1": '["a","a"]',
                    "list2": '["a","a"]',
                    "list3": '["2","2"]',
                    "list4": '["2","2"]',
                    "list5": '["true"]',
                    "list6": '["true"]',
                    "tuple1": '["a","a"]',
                    "tuple2": '["a","a"]',
                    "tuple3": '["2","2"]',
                    "tuple4": '["2","2"]',
                    "tuple5": '["true"]',
                    "tuple6": '["true"]',
                    "range1": '["0","1"]',
                    "range2": '["0","1"]',
                    "empty_list": "[]",
                    "none_list": '["hello"]',
                },
                11: {
                    "string1": "vvvvvvvvvvv",
                    "string2": "vvvvvvvvvvv",
                    "list1": '["a","a"]',
                    "list2": '["a","a"]',
                    "list3": '["2","2"]',
                    "list4": '["2","2"]',
                    "list5": '["true"]',
                    "list6": '["true"]',
                    "tuple1": '["a","a"]',
                    "tuple2": '["a","a"]',
                    "tuple3": '["2","2"]',
                    "tuple4": '["2","2"]',
                    "tuple5": '["true"]',
                    "tuple6": '["true"]',
                    "range1": '["0","1"]',
                    "range2": '["0","1"]',
                    "empty_list": "[]",
                    "none_list": '["hello"]',
                },
                128: {
                    "string1": "v" * 128,
                    "string2": "v" * 50,
                    "list1": '["a","a","a","a","a","a","a","a","a","a","a","a","a","a","a","a","a","a","a","a","a","a","a","a","a"]',
                    "list2": '["a","a","a","a","a","a","a","a","a","a"]',
                    "list3": '["2","2","2","2","2","2","2","2","2","2","2","2","2","2","2","2","2","2","2","2","2","2","2","2","2"]',
                    "list4": '["2","2","2","2","2","2","2","2","2","2"]',
                    "list5": '["true","true","true","true","true","true","true","true","true","true","true","true","true","true","true","true","true","true"]',
                    "list6": '["true","true","true","true","true","true","true","true","true","true"]',
                    "tuple1": '["a","a","a","a","a","a","a","a","a","a","a","a","a","a","a","a","a","a","a","a","a","a","a","a","a"]',
                    "tuple2": '["a","a","a","a","a","a","a","a","a","a"]',
                    "tuple3": '["2","2","2","2","2","2","2","2","2","2","2","2","2","2","2","2","2","2","2","2","2","2","2","2","2"]',
                    "tuple4": '["2","2","2","2","2","2","2","2","2","2"]',
                    "tuple5": '["true","true","true","true","true","true","true","true","true","true","true","true","true","true","true","true","true","true"]',
                    "tuple6": '["true","true","true","true","true","true","true","true","true","true"]',
                    "range1": '["0","1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16","17","18","19","20","21","22","23","24"]',
                    "range2": '["0","1","2","3","4","5","6","7","8","9"]',
                    "empty_list": "[]",
                    "none_list": '["hello",null,"world"]',
                },
            }

            return span, expected_outputs[max_tag_length]

        @staticmethod
        def get_exhaustive_otel_span_list() -> List[trace._Span]:
            trace_id = 0x6E0C63257DE34C926F9EFCD03927272E

            base_time = 683647322 * 10**9  # in ns
            start_times = (
                base_time,
                base_time + 150 * 10**6,
                base_time + 300 * 10**6,
                base_time + 400 * 10**6,
            )
            end_times = (
                start_times[0] + (50 * 10**6),
                start_times[1] + (100 * 10**6),
                start_times[2] + (200 * 10**6),
                start_times[3] + (300 * 10**6),
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
                        timestamp=base_time + 50 * 10**6,
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
                resource=trace.Resource({}),
            )
            span1.start(start_time=start_times[0])
            span1.set_attribute("key_bool", False)
            span1.set_attribute("key_string", "hello_world")
            span1.set_attribute("key_float", 111.22)
            span1.set_status(Status(StatusCode.OK))
            span1.end(end_time=end_times[0])

            span2 = trace._Span(
                name="test-span-2",
                context=parent_span_context,
                parent=None,
                resource=trace.Resource(
                    attributes={"key_resource": "some_resource"}
                ),
            )
            span2.start(start_time=start_times[1])
            span2.set_status(Status(StatusCode.ERROR, "Example description"))
            span2.end(end_time=end_times[1])

            span3 = trace._Span(
                name="test-span-3",
                context=other_context,
                parent=None,
                resource=trace.Resource(
                    attributes={"key_resource": "some_resource"}
                ),
            )
            span3.start(start_time=start_times[2])
            span3.set_attribute("key_string", "hello_world")
            span3.end(end_time=end_times[2])

            span4 = trace._Span(
                name="test-span-3",
                context=other_context,
                parent=None,
                resource=trace.Resource({}),
                instrumentation_scope=InstrumentationScope(
                    name="name", version="version"
                ),
            )
            span4.start(start_time=start_times[3])
            span4.end(end_time=end_times[3])

            return [span1, span2, span3, span4]

    # pylint: disable=W0223
    class CommonJsonEncoderTest(CommonEncoderTest, abc.ABC):
        def test_encode_trace_id(self):
            for trace_id in (1, 1024, 2**32, 2**64, 2**65):
                self.assertEqual(
                    format(trace_id, "032x"),
                    self.get_encoder_default()._encode_trace_id(trace_id),
                )

        def test_encode_span_id(self):
            for span_id in (1, 1024, 2**8, 2**16, 2**32, 2**64):
                self.assertEqual(
                    format(span_id, "016x"),
                    self.get_encoder_default()._encode_span_id(span_id),
                )

        def test_encode_local_endpoint_default(self):
            self.assertEqual(
                self.get_encoder_default()._encode_local_endpoint(
                    NodeEndpoint()
                ),
                {"serviceName": TEST_SERVICE_NAME},
            )

        def test_encode_local_endpoint_explicits(self):
            ipv4 = "192.168.0.1"
            ipv6 = "2001:db8::c001"
            port = 414120
            self.assertEqual(
                self.get_encoder_default()._encode_local_endpoint(
                    NodeEndpoint(ipv4, ipv6, port)
                ),
                {
                    "serviceName": TEST_SERVICE_NAME,
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
            self.assertEqual(expected_spans, actual_spans)
