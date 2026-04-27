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
import unittest

from requests.models import Response

from opentelemetry.exporter.otlp.proto.http._common import _parse_response_body
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsPartialSuccess,
    ExportLogsServiceResponse,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTracePartialSuccess,
    ExportTraceServiceResponse,
)


def _make_response(
    content: bytes,
    content_type: str,
    reason: str = "Bad Request",
    status_code: int = 400,
) -> Response:
    resp = Response()
    resp.status_code = status_code
    resp.reason = reason
    resp._content = content  # pylint: disable=protected-access
    resp.headers["Content-Type"] = content_type
    return resp


class TestParseResponseBody(unittest.TestCase):
    def test_protobuf_content_type_with_error_message(self):
        proto_response = ExportTraceServiceResponse(
            partial_success=ExportTracePartialSuccess(
                rejected_spans=3,
                error_message="invalid span data",
            )
        )
        resp = _make_response(
            content=proto_response.SerializeToString(),
            content_type="application/x-protobuf",
        )
        self.assertEqual(
            _parse_response_body(resp, ExportTraceServiceResponse),
            "invalid span data",
        )

    def test_protobuf_content_type_without_error_message_falls_back_to_reason(
        self,
    ):
        proto_response = ExportTraceServiceResponse()
        resp = _make_response(
            content=proto_response.SerializeToString(),
            content_type="application/x-protobuf",
            reason="Bad Request",
        )
        self.assertEqual(
            _parse_response_body(resp, ExportTraceServiceResponse),
            "Bad Request",
        )

    def test_protobuf_content_type_with_charset_parameter(self):
        proto_response = ExportTraceServiceResponse(
            partial_success=ExportTracePartialSuccess(
                error_message="quota exceeded"
            )
        )
        resp = _make_response(
            content=proto_response.SerializeToString(),
            content_type="application/x-protobuf; charset=utf-8",
        )
        self.assertEqual(
            _parse_response_body(resp, ExportTraceServiceResponse),
            "quota exceeded",
        )

    def test_json_content_type_with_partial_success_error_message(self):
        body = json.dumps(
            {"partialSuccess": {"errorMessage": "rate limit exceeded"}}
        ).encode()
        resp = _make_response(content=body, content_type="application/json")
        self.assertEqual(
            _parse_response_body(resp, ExportTraceServiceResponse),
            "rate limit exceeded",
        )

    def test_json_content_type_with_rpc_status_message(self):
        body = json.dumps({"message": "permission denied"}).encode()
        resp = _make_response(content=body, content_type="application/json")
        self.assertEqual(
            _parse_response_body(resp, ExportTraceServiceResponse),
            "permission denied",
        )

    def test_json_content_type_with_charset_parameter(self):
        body = json.dumps({"message": "not authorized"}).encode()
        resp = _make_response(
            content=body, content_type="application/json; charset=utf-8"
        )
        self.assertEqual(
            _parse_response_body(resp, ExportTraceServiceResponse),
            "not authorized",
        )

    def test_unknown_content_type_returns_text(self):
        resp = _make_response(
            content=b"something went wrong",
            content_type="text/plain",
        )
        self.assertEqual(
            _parse_response_body(resp, ExportTraceServiceResponse),
            "something went wrong",
        )

    def test_empty_body_returns_reason(self):
        resp = _make_response(
            content=b"",
            content_type="application/x-protobuf",
            reason="Service Unavailable",
        )
        self.assertEqual(
            _parse_response_body(resp, ExportTraceServiceResponse),
            "Service Unavailable",
        )

    def test_malformed_protobuf_body_falls_back_to_reason(self):
        resp = _make_response(
            content=b"\xff\xfe invalid protobuf",
            content_type="application/x-protobuf",
            reason="Bad Request",
        )
        self.assertEqual(
            _parse_response_body(resp, ExportTraceServiceResponse),
            "Bad Request",
        )

    def test_malformed_json_body_falls_back_to_text(self):
        resp = _make_response(
            content=b"not valid json {{{",
            content_type="application/json",
            reason="Bad Request",
        )
        self.assertEqual(
            _parse_response_body(resp, ExportTraceServiceResponse),
            "not valid json {{{",
        )

    def test_works_with_logs_response_class(self):
        proto_response = ExportLogsServiceResponse(
            partial_success=ExportLogsPartialSuccess(
                rejected_log_records=2,
                error_message="log quota exceeded",
            )
        )
        resp = _make_response(
            content=proto_response.SerializeToString(),
            content_type="application/x-protobuf",
        )
        self.assertEqual(
            _parse_response_body(resp, ExportLogsServiceResponse),
            "log quota exceeded",
        )


if __name__ == "__main__":
    unittest.main()
