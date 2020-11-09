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
import os
import unittest
from unittest.mock import MagicMock, patch

from opentelemetry import trace as trace_api
from opentelemetry.configuration import Configuration
from opentelemetry.exporter.zipkin import (
    ZipkinSpanExporter, DEFAULT_ENDPOINT, DEFAULT_ENCODING
)
from opentelemetry.exporter.zipkin.encoder import Encoding
from opentelemetry.exporter.zipkin.encoder.json import (
    JsonV1Encoder, JsonV2Encoder
)
from opentelemetry.exporter.zipkin.encoder.protobuf import ProtobufEncoder
from opentelemetry.exporter.zipkin.encoder.protobuf.gen import zipkin_pb2
from opentelemetry.exporter.zipkin.endpoint import Endpoint
from opentelemetry.sdk import trace
from opentelemetry.sdk.trace import Resource
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.sdk.util.instrumentation import InstrumentationInfo
from opentelemetry.trace import SpanKind, TraceFlags
from opentelemetry.trace.status import Status, StatusCode


class MockResponse:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = status_code


class TestZipkinSpanExporter(unittest.TestCase):
    def setUp(self):
        # create and save span to be used in tests
        context = trace_api.SpanContext(
            trace_id=0x000000000000000000000000DEADBEEF,
            span_id=0x00000000DEADBEF0,
            is_remote=False,
        )

        self._test_span = trace._Span("test_span", context=context)
        self._test_span.start()
        self._test_span.end()

    def tearDown(self):
        if "OTEL_EXPORTER_ZIPKIN_ENDPOINT" in os.environ:
            del os.environ["OTEL_EXPORTER_ZIPKIN_ENDPOINT"]
        if "OTEL_EXPORTER_ZIPKIN_ENCODING" in os.environ:
            del os.environ["OTEL_EXPORTER_ZIPKIN_ENCODING"]
        Configuration()._reset()  # pylint: disable=protected-access

    def test_constructor_env_var(self):
        """Test the default values assigned by constructor."""
        service_name = "my-service-name"
        endpoint = "https://foo:9911/path"
        os.environ["OTEL_EXPORTER_ZIPKIN_ENDPOINT"] = endpoint
        os.environ["OTEL_EXPORTER_ZIPKIN_ENCODING"] = Encoding.PROTOBUF.value

        exporter = ZipkinSpanExporter(service_name)

        self.assertIsInstance(exporter.encoder, ProtobufEncoder)
        self.assertEqual(
            exporter.encoder.local_endpoint.service_name, service_name
        )
        self.assertEqual(exporter.encoder.local_endpoint.ipv4, None)
        self.assertEqual(exporter.encoder.local_endpoint.ipv6, None)
        self.assertEqual(exporter.encoder.local_endpoint.port, None)

        self.assertEqual(exporter.sender.endpoint, endpoint)
        self.assertEqual(exporter.sender.encoding, Encoding.PROTOBUF)

    def test_constructor_default(self):
        """Test the default values assigned by constructor."""
        service_name = "my-service-name"
        exporter = ZipkinSpanExporter(service_name)

        self.assertIsInstance(exporter.encoder, JsonV2Encoder)
        self.assertEqual(
            exporter.encoder.local_endpoint.service_name, service_name
        )
        self.assertEqual(exporter.encoder.local_endpoint.ipv4, None)
        self.assertEqual(exporter.encoder.local_endpoint.ipv6, None)
        self.assertEqual(exporter.encoder.local_endpoint.port, None)
        self.assertEqual(exporter.sender.endpoint, DEFAULT_ENDPOINT)
        self.assertEqual(exporter.sender.encoding, DEFAULT_ENCODING)

    def test_constructor_explicit(self):
        """Test the constructor passing all the options."""
        service_name = "my-opentelemetry-zipkin"
        endpoint = "https://opentelemetry.io:15875/myapi/traces?format=zipkin"
        encoding = Encoding.PROTOBUF

        exporter = ZipkinSpanExporter(service_name, endpoint, encoding)

        self.assertIsInstance(exporter.encoder, ProtobufEncoder)
        self.assertEqual(
            exporter.encoder.local_endpoint.service_name, service_name
        )
        self.assertEqual(exporter.encoder.local_endpoint.ipv4, None)
        self.assertEqual(exporter.encoder.local_endpoint.ipv6, None)
        self.assertEqual(exporter.encoder.local_endpoint.port, None)
        self.assertEqual(exporter.sender.endpoint, endpoint)
        self.assertEqual(exporter.sender.encoding, encoding)

    @patch("requests.post")
    def test_invalid_response(self, mock_post):
        mock_post.return_value = MockResponse(404)
        spans = []
        exporter = ZipkinSpanExporter("test-service")
        status = exporter.export(spans)
        self.assertEqual(SpanExportResult.FAILURE, status)

    # pylint: disable=too-many-locals,too-many-statements
    def test_export_v1_json(self):
        span_names = ("test1", "test2", "test3", "test4")
        trace_id = 0x6E0C63257DE34C926F9EFCD03927272E
        span_id = 0x34BF92DEEFC58C92
        parent_id = 0x1111111111111111
        other_id = 0x2222222222222222

        base_time = 683647322 * 10 ** 9  # in ns
        start_times = (
            base_time,
            base_time + 150 * 10 ** 6,
            base_time + 300 * 10 ** 6,
            base_time + 400 * 10 ** 6,
        )
        durations = (50 * 10 ** 6, 100 * 10 ** 6, 200 * 10 ** 6, 300 * 10 ** 6)
        end_times = (
            start_times[0] + durations[0],
            start_times[1] + durations[1],
            start_times[2] + durations[2],
            start_times[3] + durations[3],
        )

        span_context = trace_api.SpanContext(
            trace_id,
            span_id,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )
        parent_span_context = trace_api.SpanContext(
            trace_id, parent_id, is_remote=False
        )
        other_context = trace_api.SpanContext(
            trace_id, other_id, is_remote=False
        )

        event_attributes = {
            "annotation_bool": True,
            "annotation_string": "annotation_test",
            "key_float": 0.3,
        }

        event_timestamp = base_time + 50 * 10 ** 6
        event = trace.Event(
            name="event0",
            timestamp=event_timestamp,
            attributes=event_attributes,
        )

        link_attributes = {"key_bool": True}

        link = trace_api.Link(
            context=other_context, attributes=link_attributes
        )

        otel_spans = [
            trace._Span(
                name=span_names[0],
                context=span_context,
                parent=parent_span_context,
                events=(event,),
                links=(link,),
            ),
            trace._Span(
                name=span_names[1], context=parent_span_context, parent=None
            ),
            trace._Span(
                name=span_names[2], context=other_context, parent=None
            ),
            trace._Span(
                name=span_names[3], context=other_context, parent=None
            ),
        ]

        otel_spans[0].start(start_time=start_times[0])
        otel_spans[0].resource = Resource({})
        # added here to preserve order
        otel_spans[0].set_attribute("key_bool", False)
        otel_spans[0].set_attribute("key_string", "hello_world")
        otel_spans[0].set_attribute("key_float", 111.22)
        otel_spans[0].set_status(
            Status(StatusCode.ERROR, "Example description")
        )
        otel_spans[0].end(end_time=end_times[0])

        otel_spans[1].start(start_time=start_times[1])
        otel_spans[1].resource = Resource(
            attributes={"key_resource": "some_resource"}
        )
        otel_spans[1].end(end_time=end_times[1])

        otel_spans[2].start(start_time=start_times[2])
        otel_spans[2].set_attribute("key_string", "hello_world")
        otel_spans[2].resource = Resource(
            attributes={"key_resource": "some_resource"}
        )
        otel_spans[2].end(end_time=end_times[2])

        otel_spans[3].start(start_time=start_times[3])
        otel_spans[3].resource = Resource({})
        otel_spans[3].end(end_time=end_times[3])
        otel_spans[3].instrumentation_info = InstrumentationInfo(
            name="name", version="version"
        )

        service_name = "test-service"
        local_endpoint = {"serviceName": service_name}

        expected_spans = [
            {
                "traceId": format(trace_id, "x"),
                "id": format(span_id, "x"),
                "name": span_names[0],
                "timestamp": start_times[0] // 10 ** 3,
                "duration": durations[0] // 10 ** 3,
                "annotations": [
                    {
                        "timestamp": event_timestamp // 10 ** 3,
                        "value": {
                            "event0": {
                                "annotation_bool": True,
                                "annotation_string": "annotation_test",
                                "key_float": 0.3,
                            }
                        },
                        "endpoint": local_endpoint,
                    }
                ],
                "binaryAnnotations": [
                    {
                        "key": "key_bool",
                        "value": "False",
                        "endpoint": local_endpoint,
                    },
                    {
                        "key": "key_string",
                        "value": "hello_world",
                        "endpoint": local_endpoint,
                    },
                    {
                        "key": "key_float",
                        "value": "111.22",
                        "endpoint": local_endpoint,
                    },
                    {
                        "key": "otel.status_code",
                        "value": "2",
                        "endpoint": local_endpoint,
                    },
                    {
                        "key": "otel.status_description",
                        "value": "Example description",
                        "endpoint": local_endpoint,
                    },
                ],
                "debug": True,
                "parentId": format(parent_id, "x"),
            },
            {
                "traceId": format(trace_id, "x"),
                "id": format(parent_id, "x"),
                "name": span_names[1],
                "timestamp": start_times[1] // 10 ** 3,
                "duration": durations[1] // 10 ** 3,
                "annotations": None,
                "binaryAnnotations": [
                    {
                        "key": "key_resource",
                        "value": "some_resource",
                        "endpoint": local_endpoint,
                    },
                    {
                        "key": "otel.status_code",
                        "value": "1",
                        "endpoint": local_endpoint,
                    },
                ],
            },
            {
                "traceId": format(trace_id, "x"),
                "id": format(other_id, "x"),
                "name": span_names[2],
                "timestamp": start_times[2] // 10 ** 3,
                "duration": durations[2] // 10 ** 3,
                "annotations": None,
                "binaryAnnotations": [
                    {
                        "key": "key_string",
                        "value": "hello_world",
                        "endpoint": local_endpoint,
                    },
                    {
                        "key": "key_resource",
                        "value": "some_resource",
                        "endpoint": local_endpoint,
                    },
                    {
                        "key": "otel.status_code",
                        "value": "1",
                        "endpoint": local_endpoint,
                    },
                ],
            },
            {
                "traceId": format(trace_id, "x"),
                "id": format(other_id, "x"),
                "name": span_names[3],
                "timestamp": start_times[3] // 10 ** 3,
                "duration": durations[3] // 10 ** 3,
                "annotations": None,
                "binaryAnnotations": [
                    {
                        "key": "otel.instrumentation_library.name",
                        "value": "name",
                        "endpoint": local_endpoint,
                    },
                    {
                        "key": "otel.instrumentation_library.version",
                        "value": "version",
                        "endpoint": local_endpoint,
                    },
                    {
                        "key": "otel.status_code",
                        "value": "1",
                        "endpoint": local_endpoint,
                    },
                ],
            },
        ]

        exporter = ZipkinSpanExporter(
            service_name,
            "http://localhost:9411/api/v1/spans",
            Encoding.JSON_V1,
        )
        mock_post = MagicMock()
        with patch("requests.post", mock_post):
            mock_post.return_value = MockResponse(200)
            status = exporter.export(otel_spans)
            self.assertEqual(SpanExportResult.SUCCESS, status)

        # pylint: disable=unsubscriptable-object
        kwargs = mock_post.call_args[1]

        self.assertEqual(kwargs["url"], "http://localhost:9411/api/v1/spans")
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        actual_spans = sorted(
            json.loads(kwargs["data"]), key=lambda span: span["timestamp"]
        )

        for expected, actual in zip(expected_spans, actual_spans):
            expected_annotations = expected.pop("annotations", None)
            actual_annotations = actual.pop("annotations", None)
            if actual_annotations:
                for annotation in actual_annotations:
                    annotation["value"] = json.loads(annotation["value"])

            expected_binary_annotations = sorted(
                expected.pop("binaryAnnotations", None),
                key=lambda binary_annotation: binary_annotation["key"]
            )

            actual_binary_annotations = sorted(
                actual.pop("binaryAnnotations", None),
                key=lambda binary_annotation: binary_annotation["key"]
            )

            self.assertEqual(expected, actual)
            self.assertEqual(expected_annotations, actual_annotations)
            self.assertEqual(
                expected_binary_annotations, actual_binary_annotations
            )

    def _mock_post_assert_export(
            self,
            exporter: ZipkinSpanExporter,
            input_spans: list,
            expected_output_spans: list
    ):
        mock_post = MagicMock()
        with patch("requests.post", mock_post):
            mock_post.return_value = MockResponse(200)
            status = exporter.export(input_spans)
            self.assertEqual(SpanExportResult.SUCCESS, status)

        kwargs = mock_post.call_args[1]

        self.assertEqual(kwargs["url"], exporter.sender.endpoint)
        self.assertEqual(
            kwargs["headers"]["Content-Type"], exporter.sender.content_type()
        )

        # this logic is done to account for the non-deterministic ordering of
        # dicts in python 3.5
        encoder_type = type(exporter.encoder)

        if encoder_type is JsonV1Encoder:
            actual_spans = json.loads(kwargs["data"])
            for expected_span, actual_span in zip(expected_output_spans, actual_spans):
                actual_annotations = self._pop_and_sort(
                    actual_span, "annotations", "key"
                )
                actual_binary_annotations = self._pop_and_sort(
                    actual_span, "binaryAnnotations", "key"
                )
                expected_annotations = expected_span.pop("annotations", None)
                expected_binary_annotations = expected_span.pop(
                    "binaryAnnotations", None
                )
                self.assertEqual(actual_span, expected_span)
                self.assertEqual(actual_annotations, expected_annotations)
                self.assertEqual(
                    actual_binary_annotations, expected_binary_annotations
                )
        elif encoder_type is JsonV2Encoder:
            self.assertEqual(json.loads(kwargs["data"]), expected_output_spans)

    @staticmethod
    def _pop_and_sort(source_list, source_index, sort_key):
        popped_item = source_list.pop(source_index, None)
        if popped_item is not None:
            popped_item = sorted(
                popped_item,
                key=lambda x: x[sort_key]
            )
        return popped_item

    @staticmethod
    def _json_zero_padding_get_common_objects():
        span_name = "testZeroes"
        trace_id = 0x0E0C63257DE34C926F9EFCD03927272E
        span_id = 0x04BF92DEEFC58C92
        parent_id = 0x0AAAAAAAAAAAAAAA

        start_time = 683647322 * 10 ** 9  # in ns
        duration = 50 * 10 ** 6
        end_time = start_time + duration

        span_context = trace_api.SpanContext(
            trace_id,
            span_id,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )
        parent_span_context = trace_api.SpanContext(
            trace_id, parent_id, is_remote=False
        )

        otel_span = trace._Span(
            name=span_name,
            context=span_context,
            parent=parent_span_context,
        )

        otel_span.start(start_time=start_time)
        otel_span.resource = Resource({})
        otel_span.end(end_time=end_time)

        return {
            "span_name": span_name,
            "start_time": start_time,
            "duration": duration,
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_id": parent_id,
            "spans": [otel_span]
        }

    # pylint: disable=too-many-locals
    def test_export_v1_json_zero_padding(self):
        """test that hex ids starting with 0 are properly padded to 16 or 32
         hex chars when exported
        """
        common = self._json_zero_padding_get_common_objects()
        service_name = "test-service"
        expected = [
            {
                "traceId": format(common["trace_id"], 'x').zfill(32),
                "id": format(common["span_id"], 'x').zfill(16),
                "name": common["span_name"],
                "timestamp": JsonV1Encoder.nsec_to_usec_round(
                    common["start_time"]
                ),
                "duration": JsonV1Encoder.nsec_to_usec_round(common["duration"]),
                "annotations": None,
                "binaryAnnotations": [
                    {
                        "key": "otel.status_code",
                        "value": "1",
                        "endpoint": {"serviceName": service_name},
                    },
                ],
                "debug": True,
                "parentId": format(common["parent_id"], 'x').zfill(16),
            }
        ]

        self._mock_post_assert_export(
            ZipkinSpanExporter(
                service_name,
                endpoint="http://localhost:9411/api/v1/spans",
                encoding=Encoding.JSON_V1,
            ),
            common["spans"],
            expected
        )

    # pylint: disable=too-many-locals
    def test_export_v2_json_zero_padding(self):
        """test that hex ids starting with 0 are properly padded to 16 or 32
         hex chars when exported
        """
        common = self._json_zero_padding_get_common_objects()
        service_name = "test-service"
        expected = [
            {
                "traceId": format(common["trace_id"], 'x').zfill(32),
                "id": format(common["span_id"], 'x').zfill(16),
                "name": common["span_name"],
                "timestamp": JsonV2Encoder.nsec_to_usec_round(
                    common["start_time"]
                ),
                "duration": JsonV2Encoder.nsec_to_usec_round(
                    common["duration"]
                ),
                "localEndpoint": {"serviceName": service_name},
                "kind": JsonV2Encoder.SPAN_KIND_MAP[SpanKind.INTERNAL],
                "tags": {"otel.status_code": "1"},
                "annotations": None,
                "debug": True,
                "parentId": format(common["parent_id"], 'x').zfill(16),
            }
        ]

        self._mock_post_assert_export(
            ZipkinSpanExporter(
                service_name,
                endpoint="http://localhost:9411/api/v2/spans",
                encoding=Encoding.JSON_V2,
            ),
            common["spans"],
            expected,
        )

    @staticmethod
    def _test_export_json_max_tag_length_common_objects():
        span_name = "test-span"
        trace_id = 0x0E0C63257DE34C926F9EFCD03927272E
        span_id = 0x04BF92DEEFC58C92

        start_time = 683647322 * 10 ** 9  # in ns
        duration = 50 * 10 ** 6
        end_time = start_time + duration

        span_context = trace_api.SpanContext(
            trace_id,
            span_id,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )

        span = trace._Span(name=span_name, context=span_context)

        span.start(start_time=start_time)
        span.resource = Resource({})
        span.set_attribute("k1", "v" * 500)
        span.set_attribute("k2", "v" * 50)
        span.end(end_time=end_time)

        return {
            "span_name": span_name,
            "start_time": start_time,
            "duration": duration,
            "trace_id": trace_id,
            "span_id": span_id,
            "spans": [span]
        }

    def test_export_v1_json_max_tag_length_128(self):
        self._test_export_v1_json_max_tag_length(128)

    def test_export_v1_json_max_tag_length_2(self):
        self._test_export_v1_json_max_tag_length(2)

    def _test_export_v1_json_max_tag_length(self, max_tag_value_length: int):
        common = self._test_export_json_max_tag_length_common_objects()
        service_name = "test-service"
        endpoint = "http://localhost:9411/api/v1/spans"
        local_endpoint = {"serviceName": service_name}

        k1_attr_value = common["spans"][0].attributes["k1"]
        k2_attr_value = common["spans"][0].attributes["k2"]

        expected = [
            {
                "traceId": format(common["trace_id"], 'x').zfill(32),
                "id": format(common["span_id"], 'x').zfill(16),
                "name": common["span_name"],
                "timestamp": JsonV1Encoder.nsec_to_usec_round(
                    common["start_time"]
                ),
                "duration": JsonV1Encoder.nsec_to_usec_round(common["duration"]),
                "annotations": None,
                "binaryAnnotations": [
                    {
                        "key": "k1",
                        "value": k1_attr_value[:max_tag_value_length],
                        "endpoint": local_endpoint,
                    },
                    {
                        "key": "k2",
                        "value": k2_attr_value[:max_tag_value_length],
                        "endpoint": local_endpoint,
                    },
                    {
                        "key": "otel.status_code",
                        "value": "1",
                        "endpoint": local_endpoint,
                    },
                ],
                "debug": True,
            }
        ]

        self._mock_post_assert_export(
            ZipkinSpanExporter(
                endpoint=endpoint,
                encoding=Encoding.JSON_V1,
                encoder=JsonV1Encoder(
                    Endpoint(service_name),
                    max_tag_value_length=max_tag_value_length
                )
            ),
            common["spans"],
            expected,
        )

    def test_export_v2_json_max_tag_length_128(self):
        self._test_export_v2_json_max_tag_length(128)

    def test_export_v2_json_max_tag_length_2(self):
        self._test_export_v2_json_max_tag_length(2)

    def _test_export_v2_json_max_tag_length(self, max_tag_value_length: int):
        common = self._test_export_json_max_tag_length_common_objects()
        service_name = "test-service"
        endpoint = "http://localhost:9411/api/v1/spans"

        k1_attr_value = common["spans"][0].attributes["k1"]
        k2_attr_value = common["spans"][0].attributes["k2"]

        expected = [
            {
                "traceId": format(common["trace_id"], 'x').zfill(32),
                "id": format(common["span_id"], 'x').zfill(16),
                "name": common["span_name"],
                "timestamp": JsonV2Encoder.nsec_to_usec_round(
                    common["start_time"]
                ),
                "duration": JsonV2Encoder.nsec_to_usec_round(common[
                                                                 "duration"]),
                "localEndpoint": {"serviceName": service_name},
                "kind": JsonV2Encoder.SPAN_KIND_MAP[SpanKind.INTERNAL],
                "tags": {
                    "k1": k1_attr_value[:max_tag_value_length],
                    "k2": k2_attr_value[:max_tag_value_length],
                    "otel.status_code": "1"
                },
                "annotations": None,
                "debug": True,
            }
        ]

        self._mock_post_assert_export(
            ZipkinSpanExporter(
                endpoint=endpoint,
                encoder=JsonV2Encoder(
                    Endpoint(service_name),
                    max_tag_value_length=max_tag_value_length
                )
            ),
            common["spans"],
            expected,
        )

    # pylint: disable=too-many-locals,too-many-statements
    def test_export_v2_json(self):
        span_names = ("test1", "test2", "test3", "test4")
        trace_id = 0x6E0C63257DE34C926F9EFCD03927272E
        span_id = 0x34BF92DEEFC58C92
        parent_id = 0x1111111111111111
        other_id = 0x2222222222222222

        base_time = 683647322 * 10 ** 9  # in ns
        start_times = (
            base_time,
            base_time + 150 * 10 ** 6,
            base_time + 300 * 10 ** 6,
            base_time + 400 * 10 ** 6,
        )
        durations = (50 * 10 ** 6, 100 * 10 ** 6, 200 * 10 ** 6, 300 * 10 ** 6)
        end_times = (
            start_times[0] + durations[0],
            start_times[1] + durations[1],
            start_times[2] + durations[2],
            start_times[3] + durations[3],
        )

        span_context = trace_api.SpanContext(
            trace_id,
            span_id,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )
        parent_span_context = trace_api.SpanContext(
            trace_id, parent_id, is_remote=False
        )
        other_context = trace_api.SpanContext(
            trace_id, other_id, is_remote=False
        )

        event_attributes = {
            "annotation_bool": True,
            "annotation_string": "annotation_test",
            "key_float": 0.3,
        }

        event_timestamp = base_time + 50 * 10 ** 6
        event = trace.Event(
            name="event0",
            timestamp=event_timestamp,
            attributes=event_attributes,
        )

        link_attributes = {"key_bool": True}

        link = trace_api.Link(
            context=other_context, attributes=link_attributes
        )

        otel_spans = [
            trace._Span(
                name=span_names[0],
                context=span_context,
                parent=parent_span_context,
                events=(event,),
                links=(link,),
            ),
            trace._Span(
                name=span_names[1], context=parent_span_context, parent=None
            ),
            trace._Span(
                name=span_names[2], context=other_context, parent=None
            ),
            trace._Span(
                name=span_names[3], context=other_context, parent=None
            ),
        ]

        otel_spans[0].start(start_time=start_times[0])
        otel_spans[0].resource = Resource({})
        # added here to preserve order
        otel_spans[0].set_attribute("key_bool", False)
        otel_spans[0].set_attribute("key_string", "hello_world")
        otel_spans[0].set_attribute("key_float", 111.22)
        otel_spans[0].set_status(
            Status(StatusCode.ERROR, "Example description")
        )
        otel_spans[0].end(end_time=end_times[0])

        otel_spans[1].start(start_time=start_times[1])
        otel_spans[1].resource = Resource(
            attributes={"key_resource": "some_resource"}
        )
        otel_spans[1].end(end_time=end_times[1])

        otel_spans[2].start(start_time=start_times[2])
        otel_spans[2].set_attribute("key_string", "hello_world")
        otel_spans[2].resource = Resource(
            attributes={"key_resource": "some_resource"}
        )
        otel_spans[2].end(end_time=end_times[2])

        otel_spans[3].start(start_time=start_times[3])
        otel_spans[3].resource = Resource({})
        otel_spans[3].end(end_time=end_times[3])
        otel_spans[3].instrumentation_info = InstrumentationInfo(
            name="name", version="version"
        )

        service_name = "test-service"
        local_endpoint = {"serviceName": service_name}
        span_kind = JsonV2Encoder.SPAN_KIND_MAP[SpanKind.INTERNAL]

        expected_spans = [
            {
                "traceId": format(trace_id, "x"),
                "id": format(span_id, "x"),
                "name": span_names[0],
                "timestamp": start_times[0] // 10 ** 3,
                "duration": durations[0] // 10 ** 3,
                "localEndpoint": local_endpoint,
                "kind": span_kind,
                "tags": {
                    "key_bool": "False",
                    "key_string": "hello_world",
                    "key_float": "111.22",
                    "otel.status_code": "2",
                    "otel.status_description": "Example description",
                },
                "debug": True,
                "parentId": format(parent_id, "x"),
                "annotations": [
                    {
                        "timestamp": event_timestamp // 10 ** 3,
                        "value": {
                            "event0": {
                                "annotation_bool": True,
                                "annotation_string": "annotation_test",
                                "key_float": 0.3,
                            }
                        },
                    }
                ],
            },
            {
                "traceId": format(trace_id, "x"),
                "id": format(parent_id, "x"),
                "name": span_names[1],
                "timestamp": start_times[1] // 10 ** 3,
                "duration": durations[1] // 10 ** 3,
                "localEndpoint": local_endpoint,
                "kind": span_kind,
                "tags": {
                    "key_resource": "some_resource",
                    "otel.status_code": "1",
                },
                "annotations": None,
            },
            {
                "traceId": format(trace_id, "x"),
                "id": format(other_id, "x"),
                "name": span_names[2],
                "timestamp": start_times[2] // 10 ** 3,
                "duration": durations[2] // 10 ** 3,
                "localEndpoint": local_endpoint,
                "kind": span_kind,
                "tags": {
                    "key_string": "hello_world",
                    "key_resource": "some_resource",
                    "otel.status_code": "1",
                },
                "annotations": None,
            },
            {
                "traceId": format(trace_id, "x"),
                "id": format(other_id, "x"),
                "name": span_names[3],
                "timestamp": start_times[3] // 10 ** 3,
                "duration": durations[3] // 10 ** 3,
                "localEndpoint": local_endpoint,
                "kind": span_kind,
                "tags": {
                    "otel.instrumentation_library.name": "name",
                    "otel.instrumentation_library.version": "version",
                    "otel.status_code": "1",
                },
                "annotations": None,
            },
        ]

        exporter = ZipkinSpanExporter(service_name)
        mock_post = MagicMock()
        with patch("requests.post", mock_post):
            mock_post.return_value = MockResponse(200)
            status = exporter.export(otel_spans)
            self.assertEqual(SpanExportResult.SUCCESS, status)

        # pylint: disable=unsubscriptable-object
        kwargs = mock_post.call_args[1]

        self.assertEqual(kwargs["url"], "http://localhost:9411/api/v2/spans")
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        actual_spans = sorted(
            json.loads(kwargs["data"]), key=lambda span: span["timestamp"]
        )
        for expected, actual in zip(expected_spans, actual_spans):
            expected_annotations = expected.pop("annotations", None)
            actual_annotations = actual.pop("annotations", None)
            if actual_annotations:
                for annotation in actual_annotations:
                    annotation["value"] = json.loads(annotation["value"])
            self.assertEqual(expected, actual)
            self.assertEqual(expected_annotations, actual_annotations)

    # pylint: disable=too-many-locals,too-many-statements
    def test_export_v2_protobuf(self):
        span_names = ("test1", "test2", "test3", "test4")
        trace_id = 0x6E0C63257DE34C926F9EFCD03927272E
        span_id = 0x34BF92DEEFC58C92
        parent_id = 0x1111111111111111
        other_id = 0x2222222222222222

        base_time = 683647322 * 10 ** 9  # in ns
        start_times = (
            base_time,
            base_time + 150 * 10 ** 6,
            base_time + 300 * 10 ** 6,
            base_time + 400 * 10 ** 6,
        )
        durations = (50 * 10 ** 6, 100 * 10 ** 6, 200 * 10 ** 6, 300 * 10 ** 6)
        end_times = (
            start_times[0] + durations[0],
            start_times[1] + durations[1],
            start_times[2] + durations[2],
            start_times[3] + durations[3],
        )

        span_context = trace_api.SpanContext(
            trace_id,
            span_id,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )
        parent_span_context = trace_api.SpanContext(
            trace_id, parent_id, is_remote=False
        )
        other_context = trace_api.SpanContext(
            trace_id, other_id, is_remote=False
        )

        event_attributes = {
            "annotation_bool": True,
            "annotation_string": "annotation_test",
            "key_float": 0.3,
        }

        event_timestamp = base_time + 50 * 10 ** 6
        event = trace.Event(
            name="event0",
            timestamp=event_timestamp,
            attributes=event_attributes,
        )

        link_attributes = {"key_bool": True}

        link = trace_api.Link(
            context=other_context, attributes=link_attributes
        )

        otel_spans = [
            trace._Span(
                name=span_names[0],
                context=span_context,
                parent=parent_span_context,
                events=(event,),
                links=(link,),
            ),
            trace._Span(
                name=span_names[1], context=parent_span_context, parent=None
            ),
            trace._Span(
                name=span_names[2], context=other_context, parent=None
            ),
            trace._Span(
                name=span_names[3], context=other_context, parent=None
            ),
        ]

        otel_spans[0].start(start_time=start_times[0])
        otel_spans[0].resource = Resource({})
        # added here to preserve order
        otel_spans[0].set_attribute("key_bool", False)
        otel_spans[0].set_attribute("key_string", "hello_world")
        otel_spans[0].set_attribute("key_float", 111.22)
        otel_spans[0].set_status(
            Status(StatusCode.ERROR, "Example description")
        )
        otel_spans[0].end(end_time=end_times[0])

        otel_spans[1].start(start_time=start_times[1])
        otel_spans[1].resource = Resource(
            attributes={"key_resource": "some_resource"}
        )
        otel_spans[1].end(end_time=end_times[1])

        otel_spans[2].start(start_time=start_times[2])
        otel_spans[2].set_attribute("key_string", "hello_world")
        otel_spans[2].resource = Resource(
            attributes={"key_resource": "some_resource"}
        )
        otel_spans[2].end(end_time=end_times[2])

        otel_spans[3].start(start_time=start_times[3])
        otel_spans[3].resource = Resource({})
        otel_spans[3].end(end_time=end_times[3])
        otel_spans[3].instrumentation_info = InstrumentationInfo(
            name="name", version="version"
        )

        service_name = "test-service"
        local_endpoint = zipkin_pb2.Endpoint(service_name=service_name)
        span_kind = ProtobufEncoder.SPAN_KIND_MAP[SpanKind.INTERNAL]

        expected_spans = zipkin_pb2.ListOfSpans(
            spans=[
                zipkin_pb2.Span(
                    trace_id=trace_id.to_bytes(
                        length=16, byteorder="big", signed=False
                    ),
                    id=ProtobufEncoder.encode_pbuf_span_id(span_id),
                    name=span_names[0],
                    timestamp=ProtobufEncoder.nsec_to_usec_round(
                        start_times[0]
                    ),
                    duration=ProtobufEncoder.nsec_to_usec_round(
                        durations[0]
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
                    parent_id=ProtobufEncoder.encode_pbuf_span_id(parent_id),
                    annotations=[
                        zipkin_pb2.Annotation(
                            timestamp=ProtobufEncoder.nsec_to_usec_round(
                                event_timestamp
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
                    trace_id=trace_id.to_bytes(
                        length=16, byteorder="big", signed=False
                    ),
                    id=ProtobufEncoder.encode_pbuf_span_id(parent_id),
                    name=span_names[1],
                    timestamp=ProtobufEncoder.nsec_to_usec_round(
                        start_times[1]
                    ),
                    duration=ProtobufEncoder.nsec_to_usec_round(durations[1]),
                    local_endpoint=local_endpoint,
                    kind=span_kind,
                    tags={
                        "key_resource": "some_resource",
                        "otel.status_code": "1",
                    },
                ),
                zipkin_pb2.Span(
                    trace_id=trace_id.to_bytes(
                        length=16, byteorder="big", signed=False
                    ),
                    id=ProtobufEncoder.encode_pbuf_span_id(other_id),
                    name=span_names[2],
                    timestamp=ProtobufEncoder.nsec_to_usec_round(
                        start_times[2]
                    ),
                    duration=ProtobufEncoder.nsec_to_usec_round(
                        durations[2]
                    ),
                    local_endpoint=local_endpoint,
                    kind=span_kind,
                    tags={
                        "key_string": "hello_world",
                        "key_resource": "some_resource",
                        "otel.status_code": "1",
                    },
                ),
                zipkin_pb2.Span(
                    trace_id=trace_id.to_bytes(
                        length=16, byteorder="big", signed=False
                    ),
                    id=ProtobufEncoder.encode_pbuf_span_id(other_id),
                    name=span_names[3],
                    timestamp=ProtobufEncoder.nsec_to_usec_round(
                        start_times[3]
                    ),
                    duration=ProtobufEncoder.nsec_to_usec_round(
                        durations[3]
                    ),
                    local_endpoint=local_endpoint,
                    kind=span_kind,
                    tags={
                        "otel.instrumentation_library.name": "name",
                        "otel.instrumentation_library.version": "version",
                        "otel.status_code": "1",
                    },
                ),
            ],
        )

        exporter = ZipkinSpanExporter(service_name, encoding=Encoding.PROTOBUF)
        mock_post = MagicMock()
        with patch("requests.post", mock_post):
            mock_post.return_value = MockResponse(200)
            status = exporter.export(otel_spans)
            self.assertEqual(SpanExportResult.SUCCESS, status)

        # pylint: disable=unsubscriptable-object
        kwargs = mock_post.call_args[1]

        self.assertEqual(kwargs["url"], "http://localhost:9411/api/v2/spans")
        self.assertEqual(
            kwargs["headers"]["Content-Type"], "application/x-protobuf"
        )
        self.assertEqual(
            zipkin_pb2.ListOfSpans.FromString(kwargs["data"]), expected_spans
        )

    def test_export_v2_protobuf_max_tag_length(self):
        service_name = "test-service"

        span_context = trace_api.SpanContext(
            0x0E0C63257DE34C926F9EFCD03927272E,
            0x04BF92DEEFC58C92,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )

        span = trace._Span(name="test-span", context=span_context,)

        span.start()
        span.resource = Resource({})
        # added here to preserve order
        span.set_attribute("k1", "v" * 500)
        span.set_attribute("k2", "v" * 50)
        span.set_status(Status(StatusCode.ERROR, "Example description"))
        span.end()

        exporter = ZipkinSpanExporter(
            service_name,
            encoding=Encoding.PROTOBUF,
        )
        mock_post = MagicMock()
        with patch("requests.post", mock_post):
            mock_post.return_value = MockResponse(200)
            status = exporter.export([span])
            self.assertEqual(SpanExportResult.SUCCESS, status)

        # pylint: disable=unsubscriptable-object
        kwargs = mock_post.call_args[1]
        actual_spans = zipkin_pb2.ListOfSpans.FromString(kwargs["data"])
        span_tags = actual_spans.spans[0].tags

        self.assertEqual(len(span_tags["k1"]), 128)
        self.assertEqual(len(span_tags["k2"]), 50)

        exporter = ZipkinSpanExporter(
            encoding=Encoding.PROTOBUF,
            encoder=ProtobufEncoder(
                Endpoint(service_name),
                max_tag_value_length=2,
            )
        )
        mock_post = MagicMock()
        with patch("requests.post", mock_post):
            mock_post.return_value = MockResponse(200)
            status = exporter.export([span])
            self.assertEqual(SpanExportResult.SUCCESS, status)

        # pylint: disable=unsubscriptable-object
        kwargs = mock_post.call_args[1]
        actual_spans = zipkin_pb2.ListOfSpans.FromString(kwargs["data"])
        span_tags = actual_spans.spans[0].tags

        self.assertEqual(len(span_tags["k1"]), 2)
        self.assertEqual(len(span_tags["k2"]), 2)
