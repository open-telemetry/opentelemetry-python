# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest
from json import JSONDecodeError
from unittest.mock import MagicMock, patch

import requests
import requests.exceptions
import requests.structures
from mocket import Mocket, Mocketizer, mocketize
from mocket.mocks.mockhttp import Entry

# pylint: disable-next=import-error
from opentelemetry.exporter.http.transport._requests import (
    RequestsHTTPResult,
    RequestsHTTPTransport,
)

_TEST_URL = "http://example.test/v1/traces"


class TestRequestsHTTPResult(unittest.TestCase):
    @mocketize
    def test_content_returns_body(self):
        Entry.single_register(Entry.POST, _TEST_URL, status=200, body="hello")
        result = RequestsHTTPTransport().request("POST", _TEST_URL)
        self.assertEqual(result.content(), b"hello")

    def test_content_returns_empty_bytes_when_no_response(self):
        result = RequestsHTTPResult(status_code=200, reason="OK")
        self.assertEqual(result.content(), b"")

    @mocketize
    def test_content_returns_empty_bytes_for_empty_body(self):
        Entry.single_register(Entry.POST, _TEST_URL, status=204)
        result = RequestsHTTPTransport().request("POST", _TEST_URL)
        self.assertEqual(result.content(), b"")

    @mocketize
    def test_text_uses_response_text(self):
        Entry.single_register(
            Entry.POST,
            _TEST_URL,
            status=200,
            body="hello",
        )
        result = RequestsHTTPTransport().request("POST", _TEST_URL)
        self.assertEqual(result.text(), "hello")

    def test_text_returns_empty_string_when_no_response(self):
        result = RequestsHTTPResult(status_code=200, reason="OK")
        self.assertEqual(result.text(), "")

    @mocketize
    def test_text_returns_empty_string_for_empty_body(self):
        Entry.single_register(Entry.POST, _TEST_URL, status=204)
        result = RequestsHTTPTransport().request("POST", _TEST_URL)
        self.assertEqual(result.text(), "")

    @mocketize
    def test_json_uses_response_json(self):
        Entry.single_register(
            Entry.POST,
            _TEST_URL,
            status=200,
            body='{"key": "val"}',
            headers={"Content-Type": "application/json"},
        )
        result = RequestsHTTPTransport().request("POST", _TEST_URL)
        self.assertEqual(result.json(), {"key": "val"})

    def test_json_raises_when_no_response(self):
        result = RequestsHTTPResult(status_code=200, reason="OK")
        self.assertRaises(ValueError, result.json)

    @mocketize
    def test_json_raises_for_malformed_json(self):
        Entry.single_register(
            Entry.POST,
            _TEST_URL,
            status=200,
            body="not json",
            headers={"Content-Type": "application/json"},
        )
        result = RequestsHTTPTransport().request("POST", _TEST_URL)
        self.assertRaises(JSONDecodeError, result.json)

    @mocketize
    def test_headers_returns_response_headers(self):
        Entry.single_register(
            Entry.POST,
            _TEST_URL,
            status=200,
            headers={"X-Custom": "value"},
        )
        result = RequestsHTTPTransport().request("POST", _TEST_URL)
        self.assertEqual(result.headers()["X-Custom"], "value")

    def test_headers_returns_empty_dict_when_no_response(self):
        result = RequestsHTTPResult(status_code=200, reason="OK")
        self.assertEqual(result.headers(), {})

    @mocketize
    def test_headers_are_case_insensitive(self):
        Entry.single_register(
            Entry.POST,
            _TEST_URL,
            status=200,
            headers={"X-Custom": "value"},
        )
        result = RequestsHTTPTransport().request("POST", _TEST_URL)
        headers = result.headers()
        self.assertEqual(headers["x-custom"], "value")
        self.assertEqual(headers["X-CUSTOM"], "value")
        self.assertEqual(headers["X-Custom"], "value")


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

    def test_request_passes_timeout(self):
        cases = [
            3.5,
            None,
        ]
        for timeout in cases:
            with self.subTest(timeout=timeout):
                mock_session = MagicMock(spec=requests.Session)
                mock_session.request.return_value = MagicMock(
                    status_code=200, reason="OK"
                )
                transport = RequestsHTTPTransport(session=mock_session)
                transport.request("POST", _TEST_URL, timeout=timeout)
                timeout_kwarg = mock_session.request.call_args.kwargs[
                    "timeout"
                ]
                self.assertEqual(timeout_kwarg, timeout)

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
                    transport.is_connection_error(result.error),
                    expected_is_connection_error,
                )

    def test_is_connection_error(self):
        cases = [
            (requests.exceptions.ConnectionError("error"), True),
            (requests.exceptions.ConnectTimeout("error"), True),
            (requests.exceptions.ReadTimeout("error"), True),
            (requests.exceptions.Timeout("error"), True),
            (requests.exceptions.SSLError("error"), True),
            (requests.exceptions.ProxyError("error"), True),
            (requests.exceptions.HTTPError("error"), False),
            (requests.exceptions.RequestException("error"), False),
            (RuntimeError("error"), False),
            (ValueError("error"), False),
            (None, False),
        ]
        transport = RequestsHTTPTransport(
            session=MagicMock(spec=requests.Session)
        )
        for exception, expected in cases:
            with self.subTest(error_type=type(exception).__name__):
                self.assertEqual(
                    transport.is_connection_error(exception), expected
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

    def test_create_returns_transport_instance(self):
        mock_session = MagicMock(spec=requests.Session)
        transport = RequestsHTTPTransport.create(
            True, None, session=mock_session
        )
        self.assertIsInstance(transport, RequestsHTTPTransport)

    def test_create_forwards_verify(self):
        cases = [
            (True, True),
            (False, False),
            ("/path/to/ca.pem", "/path/to/ca.pem"),
        ]
        for verify, expected in cases:
            with self.subTest(verify=verify):
                mock_session = MagicMock(spec=requests.Session)
                RequestsHTTPTransport.create(
                    verify, None, session=mock_session
                )
                self.assertEqual(mock_session.verify, expected)

    def test_create_forwards_cert(self):
        cases = [
            "/path/to/cert.pem",
            ("/path/to/cert.pem", "/path/to/key.pem"),
        ]
        for cert in cases:
            with self.subTest(cert=cert):
                mock_session = MagicMock(spec=requests.Session)
                RequestsHTTPTransport.create(True, cert, session=mock_session)
                self.assertEqual(mock_session.cert, cert)

    def test_create_forwards_session_kwarg(self):
        mock_session = MagicMock(spec=requests.Session)
        mock_session.request.return_value = MagicMock(
            status_code=200, reason="OK"
        )
        transport = RequestsHTTPTransport.create(
            True, None, session=mock_session
        )
        transport.request("POST", _TEST_URL)
        mock_session.request.assert_called_once()
