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

from google.rpc.status_pb2 import Status
from requests.models import Response

from opentelemetry.exporter.otlp.proto.http._common import _parse_response_body


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
        status = Status(code=8, message="quota exceeded for project")
        resp = _make_response(
            content=status.SerializeToString(),
            content_type="application/x-protobuf",
        )
        self.assertEqual(
            _parse_response_body(resp),
            "quota exceeded for project",
        )

    def test_protobuf_content_type_without_message_falls_back_to_reason(self):
        status = Status(code=2)
        resp = _make_response(
            content=status.SerializeToString(),
            content_type="application/x-protobuf",
            reason="Bad Request",
        )
        self.assertEqual(
            _parse_response_body(resp),
            "Bad Request",
        )

    def test_protobuf_content_type_with_charset_parameter(self):
        status = Status(code=8, message="quota exceeded")
        resp = _make_response(
            content=status.SerializeToString(),
            content_type="application/x-protobuf; charset=utf-8",
        )
        self.assertEqual(
            _parse_response_body(resp),
            "quota exceeded",
        )

    def test_json_content_type_with_partial_success_error_message(self):
        body = json.dumps(
            {"partialSuccess": {"errorMessage": "rate limit exceeded"}}
        ).encode()
        resp = _make_response(content=body, content_type="application/json")
        self.assertEqual(
            _parse_response_body(resp),
            "rate limit exceeded",
        )

    def test_json_content_type_with_rpc_status_message(self):
        body = json.dumps({"message": "permission denied"}).encode()
        resp = _make_response(content=body, content_type="application/json")
        self.assertEqual(
            _parse_response_body(resp),
            "permission denied",
        )

    def test_json_content_type_with_charset_parameter(self):
        body = json.dumps({"message": "not authorized"}).encode()
        resp = _make_response(
            content=body, content_type="application/json; charset=utf-8"
        )
        self.assertEqual(
            _parse_response_body(resp),
            "not authorized",
        )

    def test_json_partial_success_null_falls_through(self):
        body = json.dumps({"partialSuccess": None}).encode()
        resp = _make_response(content=body, content_type="application/json")
        self.assertEqual(
            _parse_response_body(resp),
            '{"partialSuccess": null}',
        )

    def test_json_partial_success_non_dict_falls_through(self):
        body = json.dumps({"partialSuccess": "x"}).encode()
        resp = _make_response(content=body, content_type="application/json")
        self.assertEqual(
            _parse_response_body(resp),
            '{"partialSuccess": "x"}',
        )

    def test_unknown_content_type_returns_text(self):
        resp = _make_response(
            content=b"something went wrong",
            content_type="text/plain",
        )
        self.assertEqual(
            _parse_response_body(resp),
            "something went wrong",
        )

    def test_empty_body_returns_reason(self):
        resp = _make_response(
            content=b"",
            content_type="application/x-protobuf",
            reason="Service Unavailable",
        )
        self.assertEqual(
            _parse_response_body(resp),
            "Service Unavailable",
        )

    def test_malformed_protobuf_body_falls_back_to_reason(self):
        resp = _make_response(
            content=b"\xff\xfe invalid protobuf",
            content_type="application/x-protobuf",
            reason="Bad Request",
        )
        self.assertEqual(
            _parse_response_body(resp),
            "Bad Request",
        )

    def test_malformed_json_body_falls_back_to_text(self):
        resp = _make_response(
            content=b"not valid json {{{",
            content_type="application/json",
            reason="Bad Request",
        )
        self.assertEqual(
            _parse_response_body(resp),
            "not valid json {{{",
        )


if __name__ == "__main__":
    unittest.main()
