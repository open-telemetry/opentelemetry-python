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

# pylint: disable=too-many-lines
import json
import os
import unittest
from typing import List
from unittest.mock import MagicMock, patch

from opentelemetry import trace as trace_api
from opentelemetry.configuration import Configuration
from opentelemetry.exporter.zipkin import (
    ZipkinSpanExporter,
    DEFAULT_ENDPOINT,
    DEFAULT_ENCODING,
    DEFAULT_SERVICE_NAME,
)
from opentelemetry.exporter.zipkin.encoder import Encoding
from opentelemetry.exporter.zipkin.encoder.json import (
    JsonV1Encoder,
    JsonV2Encoder,
)
from opentelemetry.exporter.zipkin.encoder.protobuf import ProtobufEncoder
from opentelemetry.exporter.zipkin.encoder.protobuf.gen import zipkin_pb2
from opentelemetry.exporter.zipkin.endpoint import Endpoint
from opentelemetry.exporter.zipkin.sender.http import HttpSender
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
        if "OTEL_EXPORTER_ZIPKIN_SERVICE_NAME" in os.environ:
            del os.environ["OTEL_EXPORTER_ZIPKIN_SERVICE_NAME"]
        if "OTEL_EXPORTER_ZIPKIN_ENDPOINT" in os.environ:
            del os.environ["OTEL_EXPORTER_ZIPKIN_ENDPOINT"]
        if "OTEL_EXPORTER_ZIPKIN_ENCODING" in os.environ:
            del os.environ["OTEL_EXPORTER_ZIPKIN_ENCODING"]
        Configuration()._reset()  # pylint: disable=protected-access

    def test_constructor_default(self):
        exporter = ZipkinSpanExporter()

        self.assertIsInstance(exporter.encoder, JsonV2Encoder)
        self.assertEqual(
            exporter.encoder.local_endpoint.service_name, DEFAULT_SERVICE_NAME
        )
        self.assertEqual(exporter.encoder.local_endpoint.ipv4, None)
        self.assertEqual(exporter.encoder.local_endpoint.ipv6, None)
        self.assertEqual(exporter.encoder.local_endpoint.port, None)
        self.assertIsInstance(exporter.sender, HttpSender)
        self.assertEqual(exporter.sender.endpoint, DEFAULT_ENDPOINT)
        self.assertEqual(exporter.sender.encoding, DEFAULT_ENCODING)

    def test_constructor_env_vars(self):
        os_service_name = "os-env-service-name"
        os_endpoint = "https://foo:9911/path"
        os_encoding = Encoding.PROTOBUF

        os.environ["OTEL_EXPORTER_ZIPKIN_SERVICE_NAME"] = os_service_name
        os.environ["OTEL_EXPORTER_ZIPKIN_ENDPOINT"] = os_endpoint
        os.environ["OTEL_EXPORTER_ZIPKIN_ENCODING"] = os_encoding.value

        exporter = ZipkinSpanExporter()

        self.assertIsInstance(exporter.encoder, ProtobufEncoder)
        self.assertEqual(
            exporter.encoder.local_endpoint.service_name, os_service_name
        )
        self.assertEqual(exporter.encoder.local_endpoint.ipv4, None)
        self.assertEqual(exporter.encoder.local_endpoint.ipv6, None)
        self.assertEqual(exporter.encoder.local_endpoint.port, None)
        self.assertIsInstance(exporter.sender, HttpSender)
        self.assertEqual(exporter.sender.endpoint, os_endpoint)
        self.assertEqual(exporter.sender.encoding, os_encoding)

    def test_constructor_service(self):
        service_name = "my-service-name"
        exporter = ZipkinSpanExporter(service_name)

        self.assertIsInstance(exporter.encoder, JsonV2Encoder)
        self.assertEqual(
            exporter.encoder.local_endpoint.service_name, service_name
        )
        self.assertEqual(exporter.encoder.local_endpoint.ipv4, None)
        self.assertEqual(exporter.encoder.local_endpoint.ipv6, None)
        self.assertEqual(exporter.encoder.local_endpoint.port, None)
        self.assertIsInstance(exporter.sender, HttpSender)
        self.assertEqual(exporter.sender.endpoint, DEFAULT_ENDPOINT)
        self.assertEqual(exporter.sender.encoding, DEFAULT_ENCODING)

    def test_constructor_service_endpoint_encoding(self):
        """Test the constructor for the common usage of providing the
        service_name, endpoint and encoding arguments."""
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
        self.assertIsInstance(exporter.sender, HttpSender)
        self.assertEqual(exporter.sender.endpoint, endpoint)
        self.assertEqual(exporter.sender.encoding, encoding)

    def test_constructor_sender_encoder(self):
        """Test the constructor for the more advanced use case of providing
        a sender and encoder."""
        service_name = "my-test-service"
        endpoint = "https://opentelemetry.io:15875/myapi/traces?format=zipkin"
        encoding = Encoding.PROTOBUF
        exporter = ZipkinSpanExporter(
            encoder=ProtobufEncoder(Endpoint(service_name)),
            sender=HttpSender(endpoint, encoding),
        )

        self.assertIsInstance(exporter.encoder, ProtobufEncoder)
        self.assertEqual(
            exporter.encoder.local_endpoint.service_name, service_name
        )
        self.assertEqual(exporter.encoder.local_endpoint.ipv4, None)
        self.assertEqual(exporter.encoder.local_endpoint.ipv6, None)
        self.assertEqual(exporter.encoder.local_endpoint.port, None)
        self.assertIsInstance(exporter.sender, HttpSender)
        self.assertEqual(exporter.sender.endpoint, endpoint)
        self.assertEqual(exporter.sender.encoding, encoding)

    def test_constructor_all_params_and_env_vars(self):
        """Test the scenario where all params are provided and all OS env
        vars are set.

        The result should be that the OS env vars and class defaults are
        superseded by the explicit sender and encoder provided.
        """
        os_endpoint = "https://os.env.param:9911/path"
        os_encoding = Encoding.JSON_V1
        os.environ["OTEL_EXPORTER_ZIPKIN_ENDPOINT"] = os_endpoint
        os.environ["OTEL_EXPORTER_ZIPKIN_ENCODING"] = os_encoding.value

        exporter_param_service_name = "exporter-param-service-name"
        exporter_param_endpoint = "https://constructor.param:9911/path"
        exporter_param_encoding = Encoding.JSON_V1

        encoder_param_service_name = "encoder-param-service-name"
        sender_param_encoding = Encoding.PROTOBUF
        sender_param_endpoint = "https://sender.param:9911/path"

        exporter = ZipkinSpanExporter(
            service_name=exporter_param_service_name,
            endpoint=exporter_param_endpoint,
            encoding=exporter_param_encoding,
            encoder=ProtobufEncoder(Endpoint(encoder_param_service_name)),
            sender=HttpSender(sender_param_endpoint, sender_param_encoding),
        )

        self.assertIsInstance(exporter.encoder, ProtobufEncoder)
        self.assertEqual(
            exporter.encoder.local_endpoint.service_name,
            encoder_param_service_name,
        )
        self.assertEqual(exporter.encoder.local_endpoint.ipv4, None)
        self.assertEqual(exporter.encoder.local_endpoint.ipv6, None)
        self.assertEqual(exporter.encoder.local_endpoint.port, None)
        self.assertIsInstance(exporter.sender, HttpSender)
        self.assertEqual(exporter.sender.endpoint, sender_param_endpoint)
        self.assertEqual(exporter.sender.encoding, sender_param_encoding)

    @patch("requests.post")
    def test_invalid_response(self, mock_post):
        mock_post.return_value = MockResponse(404)
        spans = []
        exporter = ZipkinSpanExporter("test-service")
        status = exporter.export(spans)
        self.assertEqual(SpanExportResult.FAILURE, status)

    # pylint: disable=too-many-locals,too-many-statements
    def test_export_json_v1(self):
        service_name = "test-service"
        local_endpoint = {"serviceName": service_name}

        otel_spans = self._get_exhaustive_otel_span_list()
        trace_id = JsonV1Encoder.encode_trace_id(
            otel_spans[0].context.trace_id
        )

        expected_encoded_output = [
            {
                "traceId": trace_id,
                "id": JsonV1Encoder.encode_span_id(
                    otel_spans[0].context.span_id
                ),
                "name": otel_spans[0].name,
                "timestamp": otel_spans[0].start_time // 10 ** 3,
                "duration": (otel_spans[0].end_time // 10 ** 3)
                - (otel_spans[0].start_time // 10 ** 3),
                "annotations": [
                    {
                        "timestamp": otel_spans[0].events[0].timestamp
                        // 10 ** 3,
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
                "parentId": JsonV1Encoder.encode_span_id(
                    otel_spans[0].parent.span_id
                ),
            },
            {
                "traceId": trace_id,
                "id": JsonV1Encoder.encode_span_id(
                    otel_spans[1].context.span_id
                ),
                "name": otel_spans[1].name,
                "timestamp": otel_spans[1].start_time // 10 ** 3,
                "duration": (otel_spans[1].end_time // 10 ** 3)
                - (otel_spans[1].start_time // 10 ** 3),
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
                "traceId": trace_id,
                "id": JsonV1Encoder.encode_span_id(
                    otel_spans[2].context.span_id
                ),
                "name": otel_spans[2].name,
                "timestamp": otel_spans[2].start_time // 10 ** 3,
                "duration": (otel_spans[2].end_time // 10 ** 3)
                - (otel_spans[2].start_time // 10 ** 3),
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
                "traceId": trace_id,
                "id": JsonV1Encoder.encode_span_id(
                    otel_spans[3].context.span_id
                ),
                "name": otel_spans[3].name,
                "timestamp": otel_spans[3].start_time // 10 ** 3,
                "duration": (otel_spans[3].end_time // 10 ** 3)
                - (otel_spans[3].start_time // 10 ** 3),
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

        self._mock_post_assert_export(
            ZipkinSpanExporter(
                service_name,
                endpoint="http://localhost:9411/api/v1/spans",
                encoding=Encoding.JSON_V1,
            ),
            otel_spans,
            expected_encoded_output,
        )

    @staticmethod
    def _json_zero_padding_get_otel_span() -> trace._Span:
        trace_id = 0x0E0C63257DE34C926F9EFCD03927272E

        start_time = 683647322 * 10 ** 9  # in ns
        duration = 50 * 10 ** 6
        end_time = start_time + duration

        otel_span = trace._Span(
            name="testZeroes",
            context=trace_api.SpanContext(
                trace_id,
                0x04BF92DEEFC58C92,
                is_remote=False,
                trace_flags=TraceFlags(TraceFlags.SAMPLED),
            ),
            parent=trace_api.SpanContext(
                trace_id, 0x0AAAAAAAAAAAAAAA, is_remote=False
            ),
        )
        otel_span.start(start_time=start_time)
        otel_span.resource = Resource({})
        otel_span.end(end_time=end_time)

        return otel_span

    # pylint: disable=too-many-locals
    def test_export_json_v1_zero_padding(self):
        """test that hex ids starting with 0 are properly padded to 16 or 32
         hex chars when exported
        """
        otel_span = self._json_zero_padding_get_otel_span()
        service_name = "test-service"
        expected_encoded_output = [
            {
                "traceId": JsonV1Encoder.encode_trace_id(
                    otel_span.context.trace_id
                ),
                "id": JsonV1Encoder.encode_span_id(otel_span.context.span_id),
                "name": otel_span.name,
                "timestamp": JsonV1Encoder.nsec_to_usec_round(
                    otel_span.start_time
                ),
                "duration": JsonV1Encoder.nsec_to_usec_round(
                    otel_span.end_time - otel_span.start_time
                ),
                "annotations": None,
                "binaryAnnotations": [
                    {
                        "key": "otel.status_code",
                        "value": "1",
                        "endpoint": {"serviceName": service_name},
                    },
                ],
                "debug": True,
                "parentId": JsonV1Encoder.encode_span_id(
                    otel_span.parent.span_id
                ),
            }
        ]

        self._mock_post_assert_export(
            ZipkinSpanExporter(
                service_name,
                endpoint="http://localhost:9411/api/v1/spans",
                encoding=Encoding.JSON_V1,
            ),
            [otel_span],
            expected_encoded_output,
        )

    # pylint: disable=too-many-locals
    def test_export_json_v2_zero_padding(self):
        """test that hex ids starting with 0 are properly padded to 16 or 32
         hex chars when exported
        """
        otel_span = self._json_zero_padding_get_otel_span()
        service_name = "test-service"
        expected_encoded_output = [
            {
                "traceId": JsonV2Encoder.encode_trace_id(
                    otel_span.context.trace_id
                ),
                "id": JsonV2Encoder.encode_span_id(otel_span.context.span_id),
                "name": otel_span.name,
                "timestamp": JsonV1Encoder.nsec_to_usec_round(
                    otel_span.start_time
                ),
                "duration": JsonV1Encoder.nsec_to_usec_round(
                    otel_span.end_time - otel_span.start_time
                ),
                "localEndpoint": {"serviceName": service_name},
                "kind": JsonV2Encoder.SPAN_KIND_MAP[SpanKind.INTERNAL],
                "tags": {"otel.status_code": "1"},
                "annotations": None,
                "debug": True,
                "parentId": JsonV2Encoder.encode_span_id(
                    otel_span.parent.span_id
                ),
            }
        ]

        self._mock_post_assert_export(
            ZipkinSpanExporter(
                service_name,
                endpoint="http://localhost:9411/api/v2/spans",
                encoding=Encoding.JSON_V2,
            ),
            [otel_span],
            expected_encoded_output,
        )

    @staticmethod
    def _test_export_max_tag_length_get_otel_span() -> trace._Span:
        start_time = 683647322 * 10 ** 9  # in ns
        duration = 50 * 10 ** 6
        end_time = start_time + duration

        otel_span = trace._Span(
            name="test-span",
            context=trace_api.SpanContext(
                0x0E0C63257DE34C926F9EFCD03927272E,
                0x04BF92DEEFC58C92,
                is_remote=False,
                trace_flags=TraceFlags(TraceFlags.SAMPLED),
            ),
        )
        otel_span.start(start_time=start_time)
        otel_span.resource = Resource({})
        otel_span.set_attribute("k1", "v" * 500)
        otel_span.set_attribute("k2", "v" * 50)
        otel_span.end(end_time=end_time)

        return otel_span

    def _test_export_json_v1_max_tag_length(self, max_tag_value_length: int):
        otel_span = self._test_export_max_tag_length_get_otel_span()
        service_name = "test-service"
        endpoint = "http://localhost:9411/api/v1/spans"
        local_endpoint = {"serviceName": service_name}
        expected_encoded_output = [
            {
                "traceId": JsonV1Encoder.encode_trace_id(
                    otel_span.context.trace_id
                ),
                "id": JsonV1Encoder.encode_span_id(otel_span.context.span_id),
                "name": otel_span.name,
                "timestamp": JsonV1Encoder.nsec_to_usec_round(
                    otel_span.start_time
                ),
                "duration": JsonV1Encoder.nsec_to_usec_round(
                    otel_span.end_time - otel_span.start_time
                ),
                "annotations": None,
                "binaryAnnotations": [
                    {
                        "key": "k1",
                        "value": otel_span.attributes["k1"][
                            :max_tag_value_length
                        ],
                        "endpoint": local_endpoint,
                    },
                    {
                        "key": "k2",
                        "value": otel_span.attributes["k2"][
                            :max_tag_value_length
                        ],
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
                    max_tag_value_length=max_tag_value_length,
                ),
            ),
            [otel_span],
            expected_encoded_output,
        )

    def test_export_json_v1_max_tag_length_128(self):
        self._test_export_json_v1_max_tag_length(128)

    def test_export_json_v1_max_tag_length_2(self):
        self._test_export_json_v1_max_tag_length(2)

    def _test_export_json_v2_max_tag_length(self, max_tag_value_length: int):
        otel_span = self._test_export_max_tag_length_get_otel_span()
        service_name = "test-service"
        expected_encoded_output = [
            {
                "traceId": JsonV2Encoder.encode_trace_id(
                    otel_span.context.trace_id
                ),
                "id": JsonV2Encoder.encode_span_id(otel_span.context.span_id),
                "name": otel_span.name,
                "timestamp": JsonV1Encoder.nsec_to_usec_round(
                    otel_span.start_time
                ),
                "duration": JsonV1Encoder.nsec_to_usec_round(
                    otel_span.end_time - otel_span.start_time
                ),
                "localEndpoint": {"serviceName": service_name},
                "kind": JsonV2Encoder.SPAN_KIND_MAP[SpanKind.INTERNAL],
                "tags": {
                    "k1": otel_span.attributes["k1"][:max_tag_value_length],
                    "k2": otel_span.attributes["k2"][:max_tag_value_length],
                    "otel.status_code": "1",
                },
                "annotations": None,
                "debug": True,
            }
        ]

        self._mock_post_assert_export(
            ZipkinSpanExporter(
                encoder=JsonV2Encoder(
                    Endpoint(service_name),
                    max_tag_value_length=max_tag_value_length,
                )
            ),
            [otel_span],
            expected_encoded_output,
        )

    def test_export_json_v2_max_tag_length_128(self):
        self._test_export_json_v2_max_tag_length(128)

    def test_export_json_v2_max_tag_length_2(self):
        self._test_export_json_v2_max_tag_length(2)

    def _test_export_protobuf_max_tag_length(self, max_tag_value_length: int):
        otel_span = self._test_export_max_tag_length_get_otel_span()
        service_name = "test-service"
        expected_encoded_output = zipkin_pb2.ListOfSpans(
            spans=[
                zipkin_pb2.Span(
                    trace_id=ProtobufEncoder.encode_trace_id(
                        otel_span.context.trace_id
                    ),
                    id=ProtobufEncoder.encode_span_id(
                        otel_span.context.span_id
                    ),
                    name=otel_span.name,
                    timestamp=ProtobufEncoder.nsec_to_usec_round(
                        otel_span.start_time
                    ),
                    duration=JsonV2Encoder.nsec_to_usec_round(
                        otel_span.end_time - otel_span.start_time
                    ),
                    local_endpoint=zipkin_pb2.Endpoint(
                        service_name=service_name
                    ),
                    kind=ProtobufEncoder.SPAN_KIND_MAP[SpanKind.INTERNAL],
                    tags={
                        "k1": otel_span.attributes["k1"][
                            :max_tag_value_length
                        ],
                        "k2": otel_span.attributes["k2"][
                            :max_tag_value_length
                        ],
                        "otel.status_code": "1",
                    },
                    annotations=None,
                    debug=True,
                )
            ]
        )

        self._mock_post_assert_export(
            ZipkinSpanExporter(
                service_name,
                encoding=Encoding.PROTOBUF,
                encoder=ProtobufEncoder(
                    Endpoint(service_name),
                    max_tag_value_length=max_tag_value_length,
                ),
            ),
            [otel_span],
            expected_encoded_output,
        )

    def test_export_protobuf_max_tag_length_128(self):
        self._test_export_protobuf_max_tag_length(128)

    def test_export_protobuf_max_tag_length_2(self):
        self._test_export_protobuf_max_tag_length(2)

    # pylint: disable=too-many-locals,too-many-statements
    def test_export_json_v2(self):
        service_name = "test-service"
        local_endpoint = {"serviceName": service_name}
        span_kind = JsonV2Encoder.SPAN_KIND_MAP[SpanKind.INTERNAL]

        otel_spans = self._get_exhaustive_otel_span_list()
        trace_id = JsonV2Encoder.encode_trace_id(
            otel_spans[0].context.trace_id
        )

        expected_encoded_output = [
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
                "debug": True,
                "parentId": JsonV2Encoder.encode_span_id(
                    otel_spans[0].parent.span_id
                ),
                "annotations": [
                    {
                        "timestamp": otel_spans[0].events[0].timestamp
                        // 10 ** 3,
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
                "traceId": trace_id,
                "id": JsonV1Encoder.encode_span_id(
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
            },
            {
                "traceId": trace_id,
                "id": JsonV1Encoder.encode_span_id(
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
            },
            {
                "traceId": trace_id,
                "id": JsonV1Encoder.encode_span_id(
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
            },
        ]

        self._mock_post_assert_export(
            ZipkinSpanExporter(service_name),
            otel_spans,
            expected_encoded_output,
        )

    # pylint: disable=too-many-locals,too-many-statements
    def test_export_protobuf(self):
        service_name = "test-service"
        local_endpoint = zipkin_pb2.Endpoint(service_name=service_name)
        span_kind = ProtobufEncoder.SPAN_KIND_MAP[SpanKind.INTERNAL]

        otel_spans = self._get_exhaustive_otel_span_list()
        trace_id = otel_spans[0].context.trace_id.to_bytes(
            length=16, byteorder="big", signed=False
        )

        expected_encoded_output = zipkin_pb2.ListOfSpans(
            spans=[
                zipkin_pb2.Span(
                    trace_id=trace_id,
                    id=ProtobufEncoder.encode_span_id(
                        otel_spans[0].context.span_id
                    ),
                    name=otel_spans[0].name,
                    timestamp=ProtobufEncoder.nsec_to_usec_round(
                        otel_spans[0].start_time
                    ),
                    duration=(
                        ProtobufEncoder.nsec_to_usec_round(
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
                    parent_id=ProtobufEncoder.encode_span_id(
                        otel_spans[0].parent.span_id
                    ),
                    annotations=[
                        zipkin_pb2.Annotation(
                            timestamp=ProtobufEncoder.nsec_to_usec_round(
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
                    id=ProtobufEncoder.encode_span_id(
                        otel_spans[1].context.span_id
                    ),
                    name=otel_spans[1].name,
                    timestamp=ProtobufEncoder.nsec_to_usec_round(
                        otel_spans[1].start_time
                    ),
                    duration=(
                        ProtobufEncoder.nsec_to_usec_round(
                            otel_spans[1].end_time - otel_spans[1].start_time
                        )
                    ),
                    local_endpoint=local_endpoint,
                    kind=span_kind,
                    tags={
                        "key_resource": "some_resource",
                        "otel.status_code": "1",
                    },
                ),
                zipkin_pb2.Span(
                    trace_id=trace_id,
                    id=ProtobufEncoder.encode_span_id(
                        otel_spans[2].context.span_id
                    ),
                    name=otel_spans[2].name,
                    timestamp=ProtobufEncoder.nsec_to_usec_round(
                        otel_spans[2].start_time
                    ),
                    duration=(
                        ProtobufEncoder.nsec_to_usec_round(
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
                ),
                zipkin_pb2.Span(
                    trace_id=trace_id,
                    id=ProtobufEncoder.encode_span_id(
                        otel_spans[3].context.span_id
                    ),
                    name=otel_spans[3].name,
                    timestamp=ProtobufEncoder.nsec_to_usec_round(
                        otel_spans[3].start_time
                    ),
                    duration=(
                        ProtobufEncoder.nsec_to_usec_round(
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
                ),
            ],
        )

        self._mock_post_assert_export(
            ZipkinSpanExporter(service_name, encoding=Encoding.PROTOBUF),
            otel_spans,
            expected_encoded_output,
        )

    def _mock_post_assert_export(
        self,
        exporter: ZipkinSpanExporter,
        otel_spans: List[trace._Span],
        expected_encoded_output: list,
    ):
        """
        Convenience function to perform a mock export for the provided exporter
        and spans and then verify that the output is as expected (URL
        endpoint, HTTP content type and the span data).

        :param exporter: ZipkinSpanExporter
        :param otel_spans: a list of trace._Span objects that will be mock
        exported
        :param expected_encoded_output: a 1:1 list corresponding to
        otel_spans which provides the expected encoded output of each span
        """
        mock_post = MagicMock()
        with patch("requests.post", mock_post):
            mock_post.return_value = MockResponse(200)
            status = exporter.export(otel_spans)
            self.assertEqual(SpanExportResult.SUCCESS, status)

        # pylint: disable=unsubscriptable-object
        kwargs = mock_post.call_args[1]

        self.assertEqual(kwargs["url"], exporter.sender.endpoint)
        self.assertEqual(
            kwargs["headers"]["Content-Type"], exporter.sender.content_type()
        )

        # this logic is done to account for the non-deterministic ordering of
        # dicts in python 3.5
        encoder_type = type(exporter.encoder)

        if encoder_type is JsonV1Encoder:
            actual_spans = sorted(
                json.loads(kwargs["data"]), key=lambda span: span["timestamp"]
            )
            for expected_span, actual_span in zip(
                expected_encoded_output, actual_spans
            ):
                actual_annotations = self._pop_and_sort(
                    actual_span, "annotations", "timestamp"
                )
                if actual_annotations:
                    for annotation in actual_annotations:
                        annotation["value"] = json.loads(annotation["value"])
                actual_binary_annotations = self._pop_and_sort(
                    actual_span, "binaryAnnotations", "key"
                )
                expected_annotations = self._pop_and_sort(
                    expected_span, "annotations", "timestamp"
                )
                expected_binary_annotations = self._pop_and_sort(
                    expected_span, "binaryAnnotations", "key"
                )
                self.assertEqual(actual_span, expected_span)
                self.assertEqual(actual_annotations, expected_annotations)
                self.assertEqual(
                    actual_binary_annotations, expected_binary_annotations
                )
        elif encoder_type is JsonV2Encoder:
            actual_spans = json.loads(kwargs["data"])
            for expected_span, actual_span in zip(
                expected_encoded_output, actual_spans
            ):
                actual_annotations = self._pop_and_sort(
                    actual_span, "annotations", "timestamp"
                )
                if actual_annotations:
                    for annotation in actual_annotations:
                        annotation["value"] = json.loads(annotation["value"])
                expected_annotations = expected_span.pop("annotations", None)
                self.assertEqual(actual_span, expected_span)
                self.assertEqual(actual_annotations, expected_annotations)
        elif encoder_type is ProtobufEncoder:
            actual_spans = zipkin_pb2.ListOfSpans.FromString(kwargs["data"])
            self.assertEqual(actual_spans, expected_encoded_output)

    @staticmethod
    def _pop_and_sort(source_list, source_index, sort_key):
        """
        Convenience method that will pop a specified index from a list,
        sort it by a given key and then return it.
        """
        popped_item = source_list.pop(source_index, None)
        if popped_item is not None:
            popped_item = sorted(popped_item, key=lambda x: x[sort_key])
        return popped_item

    @staticmethod
    def _get_exhaustive_otel_span_list() -> List[trace._Span]:
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
        span1.resource = Resource({})
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
        span2.resource = Resource(attributes={"key_resource": "some_resource"})
        span2.end(end_time=end_times[1])

        span3 = trace._Span(
            name="test-span-3", context=other_context, parent=None
        )
        span3.start(start_time=start_times[2])
        span3.set_attribute("key_string", "hello_world")
        span3.resource = Resource(attributes={"key_resource": "some_resource"})
        span3.end(end_time=end_times[2])

        span4 = trace._Span(
            name="test-span-3", context=other_context, parent=None
        )
        span4.start(start_time=start_times[3])
        span4.resource = Resource({})
        span4.end(end_time=end_times[3])
        span4.instrumentation_info = InstrumentationInfo(
            name="name", version="version"
        )

        return [span1, span2, span3, span4]
