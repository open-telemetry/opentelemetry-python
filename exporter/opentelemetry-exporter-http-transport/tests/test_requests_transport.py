# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import requests
import requests.exceptions
from mocket import Mocket, Mocketizer, mocketize
from mocket.mocks.mockhttp import Entry

# pylint: disable-next=import-error
from opentelemetry.exporter.http.transport._requests import (
    RequestsHTTPResult,
    RequestsHTTPTransport,
)

_TEST_URL = "http://example.test/v1/traces"


class TestRequestsHTTPResult(unittest.TestCase):
    def test_is_connection_error(self):
        cases = [
            (RequestsHTTPResult(status_code=200, reason="OK"), False),
            (
                RequestsHTTPResult(
                    error=requests.exceptions.ConnectionError("error")
                ),
                True,
            ),
            (
                RequestsHTTPResult(
                    error=requests.exceptions.ConnectTimeout("error")
                ),
                True,
            ),
            (
                RequestsHTTPResult(
                    error=requests.exceptions.ReadTimeout("error")
                ),
                True,
            ),
            (
                RequestsHTTPResult(error=requests.exceptions.Timeout("error")),
                True,
            ),
            (
                RequestsHTTPResult(
                    error=requests.exceptions.SSLError("error")
                ),
                True,
            ),
            (
                RequestsHTTPResult(
                    error=requests.exceptions.ProxyError("error")
                ),
                True,
            ),
            (
                RequestsHTTPResult(
                    error=requests.exceptions.HTTPError("error")
                ),
                False,
            ),
            (
                RequestsHTTPResult(
                    error=requests.exceptions.RequestException("error")
                ),
                False,
            ),
            (RequestsHTTPResult(error=RuntimeError("error")), False),
            (RequestsHTTPResult(error=ValueError("error")), False),
        ]
        for result, expected in cases:
            with self.subTest(error_type=type(result.error).__name__):
                self.assertEqual(result.is_connection_error(), expected)


# pylint: disable=protected-access,no-self-use
class TestRequestsHTTPTransport(unittest.TestCase):
    def test_request_returns_status_code_and_reason(self):
        cases = [
            (200, "OK"),
            (400, "Bad Request"),
            (503, "Service Unavailable"),
        ]
        for status_code, reason in cases:
            with self.subTest(status_code=status_code):
                with Mocketizer():
                    Entry.single_register(
                        Entry.POST, _TEST_URL, status=status_code
                    )
                    transport = RequestsHTTPTransport()
                    result = transport.request("POST", _TEST_URL)
                    self.assertEqual(result.status_code, status_code)
                    self.assertEqual(result.reason, reason)
                    self.assertIsNone(result.error)

    @mocketize
    def test_request_result_is_not_a_connection_error(self):
        Entry.single_register(Entry.POST, _TEST_URL, status=200)
        transport = RequestsHTTPTransport()
        result = transport.request("POST", _TEST_URL)
        self.assertFalse(result.is_connection_error())

    @mocketize
    def test_request_forwards_headers(self):
        headers = {
            "content-type": "application/x-protobuf",
            "x-custom": "value",
        }
        Entry.single_register(Entry.POST, _TEST_URL, status=200)
        transport = RequestsHTTPTransport()
        result = transport.request("POST", _TEST_URL, headers=headers)
        self.assertEqual(result.status_code, 200)
        req = Mocket.last_request()
        for key, value in headers.items():
            self.assertEqual(req.headers[key], value)

    @mocketize
    def test_request_forwards_data(self):
        Entry.single_register(Entry.POST, _TEST_URL, status=200)
        transport = RequestsHTTPTransport()
        result = transport.request("POST", _TEST_URL, data=b"payload")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(Mocket.last_request().body, "payload")

    def test_request_catches_exception(self):
        cases = [
            (RuntimeError("unexpected"), False),
            (requests.exceptions.ConnectionError("failed"), True),
        ]
        for error, expected_is_connection_error in cases:
            with self.subTest(error_type=type(error).__name__):
                with patch("requests.Session.request", side_effect=error):
                    transport = RequestsHTTPTransport()
                    result = transport.request("POST", _TEST_URL)
                self.assertIsNone(result.status_code)
                self.assertIsNone(result.reason)
                self.assertIs(result.error, error)
                self.assertEqual(
                    result.is_connection_error(), expected_is_connection_error
                )

    def test_verify_sets_session_verify(self):
        cases = [
            (True, True),
            (False, False),
            ("/path/to/ca.pem", "/path/to/ca.pem"),
        ]
        for verify, expected in cases:
            with self.subTest(verify=verify):
                mock_session = MagicMock(spec=requests.Session)
                RequestsHTTPTransport(verify=verify, session=mock_session)
                self.assertEqual(mock_session.verify, expected)

    def test_cert_none_does_not_set_session_cert(self):
        mock_session = MagicMock(spec=requests.Session)
        RequestsHTTPTransport(cert=None, session=mock_session)
        self.assertFalse(hasattr(mock_session, "cert"))

    def test_cert_sets_session_cert(self):
        cases = [
            "/path/to/cert.pem",
            ("/path/to/cert.pem", "/path/to/key.pem"),
        ]
        for cert in cases:
            with self.subTest(cert=cert):
                mock_session = MagicMock(spec=requests.Session)
                RequestsHTTPTransport(cert=cert, session=mock_session)
                self.assertEqual(mock_session.cert, cert)

    def test_custom_session_is_used(self):
        mock_session = MagicMock(spec=requests.Session)
        mock_session.request.return_value = MagicMock(
            status_code=200, reason="OK"
        )
        transport = RequestsHTTPTransport(session=mock_session)
        result = transport.request("POST", _TEST_URL)
        mock_session.request.assert_called_once()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.reason, "OK")

    def test_close_closes_session(self):
        mock_session = MagicMock(spec=requests.Session)
        transport = RequestsHTTPTransport(session=mock_session)
        transport.close()
        mock_session.close.assert_called_once()
