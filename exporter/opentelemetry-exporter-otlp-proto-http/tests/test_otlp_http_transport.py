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

import unittest
from unittest.mock import Mock, patch

import requests
import urllib3
from requests.models import Response

from opentelemetry.exporter.otlp.proto.http._common import (
    _transport_from_args,
)
from opentelemetry.exporter.otlp.proto.http._transport._requests import (
    RequestsHTTPResult,
    RequestsHTTPTransport,
)
from opentelemetry.exporter.otlp.proto.http._transport._urllib3 import (
    Urllib3HTTPResult,
    Urllib3HTTPTransport,
)


# pylint: disable=protected-access
class TestRequestsHTTPTransport(unittest.TestCase):
    def test_constructor_configures_session(self):
        session = requests.Session()

        transport = RequestsHTTPTransport(
            verify="certificate.pem",
            cert=("client-cert.pem", "client-key.pem"),
            session=session,
        )

        self.assertIs(transport._session, session)
        self.assertEqual(session.verify, "certificate.pem")
        self.assertEqual(session.cert, ("client-cert.pem", "client-key.pem"))

    @patch.object(requests.Session, "request")
    def test_request_returns_response_result(self, mock_request):
        response = Response()
        response.status_code = 202
        response.reason = "Accepted"
        mock_request.return_value = response
        transport = RequestsHTTPTransport(session=requests.Session())

        result = transport.request(
            "POST",
            "http://example.test/v1/traces",
            headers={"content-type": "application/x-protobuf"},
            data=b"payload",
            timeout=1.5,
        )

        self.assertEqual(result.status_code, 202)
        self.assertEqual(result.reason, "Accepted")
        self.assertIsNone(result.error)
        mock_request.assert_called_once_with(
            method="POST",
            url="http://example.test/v1/traces",
            headers={"content-type": "application/x-protobuf"},
            data=b"payload",
            timeout=1.5,
            allow_redirects=False,
        )

    def test_request_returns_error_result(self):
        session = Mock(spec=requests.Session)
        error = requests.exceptions.RequestException("request failed")
        session.request.side_effect = error
        transport = RequestsHTTPTransport(session=session)

        result = transport.request("POST", "http://example.test/v1/traces")

        self.assertIsNone(result.status_code)
        self.assertIsNone(result.reason)
        self.assertIs(result.error, error)

    def test_result_identifies_connection_errors(self):
        connection_errors = (
            requests.exceptions.ConnectionError("connection"),
            requests.exceptions.ConnectTimeout("connect timeout"),
            requests.exceptions.ReadTimeout("read timeout"),
            requests.exceptions.Timeout("timeout"),
            requests.exceptions.SSLError("ssl"),
            requests.exceptions.ProxyError("proxy"),
        )

        for error in connection_errors:
            with self.subTest(error=type(error).__name__):
                self.assertTrue(
                    RequestsHTTPResult(error=error).is_connection_error()
                )

        with self.subTest(error="RequestException"):
            self.assertFalse(
                RequestsHTTPResult(
                    error=requests.exceptions.RequestException("request")
                ).is_connection_error()
            )

        with self.subTest(error=None):
            self.assertFalse(RequestsHTTPResult().is_connection_error())

    def test_close_closes_session(self):
        session = Mock(spec=requests.Session)
        transport = RequestsHTTPTransport(session=session)

        self.assertIs(transport._session, session)
        transport.close()

        session.close.assert_called_once_with()


class TestUrllib3HTTPTransport(unittest.TestCase):
    @patch("urllib3.PoolManager")
    def test_constructor_configures_pool_manager(self, mock_pool_manager):
        cases = (
            (
                {"verify": True, "cert": None},
                {"cert_reqs": "CERT_REQUIRED"},
            ),
            (
                {"verify": False, "cert": None},
                {"cert_reqs": "CERT_NONE"},
            ),
            (
                {"verify": "certificate.pem", "cert": None},
                {
                    "cert_reqs": "CERT_REQUIRED",
                    "ca_certs": "certificate.pem",
                },
            ),
            (
                {"verify": True, "cert": "client-cert.pem"},
                {
                    "cert_reqs": "CERT_REQUIRED",
                    "cert_file": "client-cert.pem",
                },
            ),
            (
                {
                    "verify": True,
                    "cert": ("client-cert.pem", "client-key.pem"),
                },
                {
                    "cert_reqs": "CERT_REQUIRED",
                    "cert_file": "client-cert.pem",
                    "key_file": "client-key.pem",
                },
            ),
        )

        for kwargs, expected_pool_kwargs in cases:
            with self.subTest(**kwargs):
                mock_pool_manager.reset_mock()

                Urllib3HTTPTransport(**kwargs)

                mock_pool_manager.assert_called_once()
                pool_kwargs = mock_pool_manager.call_args.kwargs
                retries = pool_kwargs.pop("retries")
                self.assertIsInstance(retries, urllib3.Retry)
                self.assertEqual(retries.total, 0)
                self.assertFalse(retries.redirect)
                self.assertEqual(pool_kwargs, expected_pool_kwargs)

    @patch("urllib3.PoolManager")
    def test_request_returns_response_result(self, mock_pool_manager):
        pool = mock_pool_manager.return_value
        pool.request.return_value = Mock(status=204, reason="No Content")
        transport = Urllib3HTTPTransport()

        result = transport.request(
            "POST",
            "http://example.test/v1/metrics",
            headers={"content-type": "application/x-protobuf"},
            data=b"payload",
            timeout=2.5,
        )

        self.assertEqual(result.status_code, 204)
        self.assertEqual(result.reason, "No Content")
        self.assertIsNone(result.error)
        pool.request.assert_called_once()
        self.assertEqual(pool.request.call_args.kwargs["method"], "POST")
        self.assertEqual(
            pool.request.call_args.kwargs["url"],
            "http://example.test/v1/metrics",
        )
        self.assertEqual(
            pool.request.call_args.kwargs["headers"],
            {"content-type": "application/x-protobuf"},
        )
        self.assertEqual(pool.request.call_args.kwargs["body"], b"payload")
        self.assertTrue(pool.request.call_args.kwargs["preload_content"])
        timeout = pool.request.call_args.kwargs["timeout"]
        self.assertIsInstance(timeout, urllib3.Timeout)
        self.assertEqual(timeout.total, 2.5)

    @patch("urllib3.PoolManager")
    def test_request_without_timeout_uses_no_timeout(self, mock_pool_manager):
        pool = mock_pool_manager.return_value
        pool.request.return_value = Mock(status=200, reason="OK")
        transport = Urllib3HTTPTransport()

        result = transport.request("POST", "http://example.test/v1/logs")

        self.assertEqual(result.status_code, 200)
        self.assertIsNone(pool.request.call_args.kwargs["timeout"])

    @patch("urllib3.PoolManager")
    def test_request_returns_error_result(self, mock_pool_manager):
        error = urllib3.exceptions.HTTPError("request failed")
        pool = mock_pool_manager.return_value
        pool.request.side_effect = error
        transport = Urllib3HTTPTransport()

        result = transport.request("POST", "http://example.test/v1/logs")

        self.assertIsNone(result.status_code)
        self.assertIsNone(result.reason)
        self.assertIs(result.error, error)

    def test_result_identifies_connection_errors(self):
        connection_errors = (
            urllib3.exceptions.ConnectionError("connection"),
            urllib3.exceptions.NewConnectionError(None, "new connection"),
            urllib3.exceptions.ConnectTimeoutError(
                None, "http://example.test", "connect timeout"
            ),
            urllib3.exceptions.MaxRetryError(
                None, "http://example.test", "max retry"
            ),
            urllib3.exceptions.ProtocolError("protocol"),
        )

        for error in connection_errors:
            with self.subTest(error=type(error).__name__):
                self.assertTrue(
                    Urllib3HTTPResult(error=error).is_connection_error()
                )

        with self.subTest(error="HTTPError"):
            self.assertFalse(
                Urllib3HTTPResult(
                    error=urllib3.exceptions.HTTPError("request")
                ).is_connection_error()
            )

        with self.subTest(error=None):
            self.assertFalse(Urllib3HTTPResult().is_connection_error())

    @patch("urllib3.PoolManager")
    def test_close_clears_pool(self, mock_pool_manager):
        pool = mock_pool_manager.return_value
        transport = Urllib3HTTPTransport()

        self.assertIs(transport._pool, pool)
        transport.close()

        pool.clear.assert_called_once_with()


class TestTransportFromArgs(unittest.TestCase):
    def test_returns_requests_transport_for_session(self):
        session = requests.Session()

        transport = _transport_from_args(session, True, None)

        self.assertIsInstance(transport, RequestsHTTPTransport)
        self.assertIs(transport._session, session)

    @patch("urllib3.PoolManager")
    def test_returns_urllib3_transport_without_session(
        self, mock_pool_manager
    ):
        transport = _transport_from_args(None, True, None)

        self.assertIsInstance(transport, Urllib3HTTPTransport)
        mock_pool_manager.assert_called_once()
