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

import gzip
import unittest
import zlib
from io import BytesIO
from unittest.mock import patch

from opentelemetry.exporter.otlp.sender.http import HttpSender
from opentelemetry.exporter.otlp.util import Compression, Headers


class MockResponse:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = status_code


class TestHttpSender(unittest.TestCase):
    def test_constructor_defaults(self):
        sender = HttpSender()
        self.assertEqual(sender._endpoint, None)
        self.assertEqual(sender._insecure, False)
        self.assertEqual(sender._certificate_file, None)
        self.assertEqual(sender._timeout, None)
        self.assertEqual(sender._compression, None)
        self.assertEqual(sender._headers, {})

    def test_constructor_explicits(self):
        sender = HttpSender(
            endpoint="test.endpoint.com/v2/api",
            insecure=True,
            certificate_file="path/to/service.crt",
            timeout=33,
            compression=Compression.GZIP,
            headers={"key1": "val1", "key2": "val2"},
        )
        self.assertEqual(sender._endpoint, "test.endpoint.com/v2/api")
        self.assertEqual(sender._insecure, True)
        self.assertEqual(sender._certificate_file, "path/to/service.crt")
        self.assertEqual(sender._timeout, 33)
        self.assertEqual(sender._compression, Compression.GZIP)
        self.assertEqual(sender._headers, {"key1": "val1", "key2": "val2"})

    @patch("requests.post")
    def test_send_http_response_status_code_200_success(self, mock_post):
        mock_post.return_value = MockResponse(200)
        result = HttpSender().send("serialized spans", "application/json")
        self.assertTrue(result)

    @patch("requests.post")
    def test_send_http_response_status_code_202_success(self, mock_post):
        mock_post.return_value = MockResponse(202)
        result = HttpSender().send("serialized spans", "application/json")
        self.assertTrue(result)

    @patch("requests.post")
    def test_send_http_response_status_code_400_failure(self, mock_post):
        mock_post.return_value = MockResponse(400)
        with self.assertLogs(level="ERROR") as cm:
            result = HttpSender().send("serialized spans", "application/json")
        self.assertFalse(result)
        self.assertEqual(
            cm.output[0],
            "ERROR:opentelemetry.exporter.otlp.sender.http:Traces cannot be uploaded; status code: 400, message 400",
        )

    @patch("requests.post")
    def test_send_set_endpoint(self, mock_post):
        mock_post.return_value = MockResponse(200)
        sender = HttpSender(endpoint="test.endpoint.com/v2/api")
        sender.send("serialized spans", "application/json")

        self.assertEqual(mock_post.call_args[0][0], "test.endpoint.com/v2/api")

    @patch("requests.post")
    def test_send_set_headers(self, mock_post):
        mock_post.return_value = MockResponse(200)
        sender = HttpSender(headers={"key1": "val1", "key2": "val2"})
        sender.send("serialized spans", "application/json")

        kwargs = mock_post.call_args[1]
        self.assertEqual(
            kwargs["headers"],
            {
                "key1": "val1",
                "key2": "val2",
                "Content-Type": "application/json",
            },
        )

    @patch("requests.post")
    def test_send_set_headers_content_type_collision(self, mock_post):
        """
        The content type passed into the send() call should win and override
        any content type that was provided when constructing the sender.
        """
        mock_post.return_value = MockResponse(200)
        sender = HttpSender(headers={"key1": "val1", "Content-Type": "junk"})
        sender.send("serialized spans", "application/json")

        kwargs = mock_post.call_args[1]
        self.assertEqual(
            kwargs["headers"],
            {"key1": "val1", "Content-Type": "application/json"},
        )

    @patch("requests.post")
    def test_send_set_timeout(self, mock_post):
        mock_post.return_value = MockResponse(200)
        sender = HttpSender(timeout=33)
        sender.send("serialized spans", "application/json")

        kwargs = mock_post.call_args[1]
        self.assertEqual(kwargs["timeout"], float(33))

    @patch("requests.post")
    def test_send_set_verify(self, mock_post):
        mock_post.return_value = MockResponse(200)
        sender = HttpSender(
            insecure=False, certificate_file="path/to/service.crt"
        )
        sender.send("serialized spans", "application/json")

        kwargs = mock_post.call_args[1]
        self.assertEqual(kwargs["verify"], "path/to/service.crt")

    @patch("requests.post")
    def test_send_set_compression_gzip(self, mock_post):
        mock_post.return_value = MockResponse(200)
        serialized_bytes = bytes("serialized spans", "utf-8")
        sender = HttpSender(compression=Compression.GZIP)
        sender.send(serialized_bytes, "application/json")

        gzip_data = BytesIO()
        with gzip.GzipFile(fileobj=gzip_data, mode="w") as f:
            f.write(serialized_bytes)

        kwargs = mock_post.call_args[1]
        self.assertEqual(kwargs["headers"]["Content-Encoding"], "gzip")
        self.assertEqual(kwargs["data"], gzip_data.getvalue())

    @patch("requests.post")
    def test_send_set_compression_deflate(self, mock_post):
        mock_post.return_value = MockResponse(200)
        serialized_bytes = bytes("serialized spans", "utf-8")
        sender = HttpSender(compression=Compression.DEFLATE)
        sender.send(serialized_bytes, "application/json")

        kwargs = mock_post.call_args[1]
        self.assertEqual(kwargs["headers"]["Content-Encoding"], "deflate")
        self.assertEqual(kwargs["data"], zlib.compress(serialized_bytes))

    @patch("requests.post")
    def test_send_set_compression_none(self, mock_post):
        mock_post.return_value = MockResponse(200)
        serialized_bytes = bytes("serialized spans", "utf-8")
        sender = HttpSender(compression=Compression.NONE)
        sender.send(serialized_bytes, "application/json")

        kwargs = mock_post.call_args[1]
        self.assertNotIn("Content-Encoding", kwargs["headers"])
        self.assertEqual(kwargs["data"], serialized_bytes)
