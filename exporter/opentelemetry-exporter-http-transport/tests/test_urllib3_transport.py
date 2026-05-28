# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest
from json import JSONDecodeError
from unittest.mock import MagicMock, patch

import urllib3
import urllib3.exceptions
from mocket import Mocket, Mocketizer, mocketize
from mocket.mocks.mockhttp import Entry
from urllib3._collections import HTTPHeaderDict

# pylint: disable-next=import-error
from opentelemetry.exporter.http.transport._urllib3 import (
    Urllib3HTTPResult,
    Urllib3HTTPTransport,
)

_TEST_URL = "http://example.test/v1/traces"


class TestUrllib3HTTPResult(unittest.TestCase):
    @mocketize
    def test_content_returns_body(self):
        Entry.single_register(Entry.POST, _TEST_URL, status=200, body="hello")
        result = Urllib3HTTPTransport().request("POST", _TEST_URL)
        self.assertEqual(result.content(), b"hello")

    def test_content_returns_empty_bytes_when_no_response(self):
        result = Urllib3HTTPResult(status_code=200, reason="OK")
        self.assertEqual(result.content(), b"")

    @mocketize
    def test_content_returns_empty_bytes_for_empty_body(self):
        Entry.single_register(Entry.POST, _TEST_URL, status=204)
        result = Urllib3HTTPTransport().request("POST", _TEST_URL)
        self.assertEqual(result.content(), b"")

    @mocketize
    def test_text_decodes_utf8(self):
        Entry.single_register(Entry.POST, _TEST_URL, status=200, body="hello")
        result = Urllib3HTTPTransport().request("POST", _TEST_URL)
        self.assertEqual(result.text(), "hello")

    def test_text_returns_empty_string_when_no_response(self):
        result = Urllib3HTTPResult(status_code=200, reason="OK")
        self.assertEqual(result.text(), "")

    @mocketize
    def test_text_returns_empty_string_for_empty_body(self):
        Entry.single_register(Entry.POST, _TEST_URL, status=204)
        result = Urllib3HTTPTransport().request("POST", _TEST_URL)
        self.assertEqual(result.text(), "")

    def test_text_raises_for_non_utf8_content(self):
        mock_response = MagicMock()
        mock_response.data = b"\xff\xfe"
        result = Urllib3HTTPResult(
            status_code=200, reason="OK", response=mock_response
        )
        self.assertRaises(UnicodeDecodeError, result.text)

    @mocketize
    def test_json_parses_dict(self):
        Entry.single_register(
            Entry.POST,
            _TEST_URL,
            status=200,
            body='{"key": "val"}',
            headers={"Content-Type": "application/json"},
        )
        result = Urllib3HTTPTransport().request("POST", _TEST_URL)
        self.assertEqual(result.json(), {"key": "val"})

    def test_json_raises_when_no_response(self):
        result = Urllib3HTTPResult(status_code=200, reason="OK")
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
        result = Urllib3HTTPTransport().request("POST", _TEST_URL)
        self.assertRaises(JSONDecodeError, result.json)

    @mocketize
    def test_headers_returns_response_headers(self):
        Entry.single_register(
            Entry.POST,
            _TEST_URL,
            status=200,
            headers={"X-Custom": "value"},
        )
        result = Urllib3HTTPTransport().request("POST", _TEST_URL)
        self.assertEqual(result.headers()["X-Custom"], "value")

    def test_headers_raises_when_no_response(self):
        result = Urllib3HTTPResult(status_code=200, reason="OK")
        self.assertRaises(ValueError, result.headers)

    @mocketize
    def test_headers_are_case_insensitive(self):
        Entry.single_register(
            Entry.POST,
            _TEST_URL,
            status=200,
            headers={"X-Custom": "value"},
        )
        result = Urllib3HTTPTransport().request("POST", _TEST_URL)
        headers = result.headers()
        self.assertEqual(headers["x-custom"], "value")
        self.assertEqual(headers["X-CUSTOM"], "value")
        self.assertEqual(headers["X-Custom"], "value")

    def test_headers_returns_multiple_values_as_comma_separated(self):
        mock_response = MagicMock()
        headers = HTTPHeaderDict()
        headers.add("X-Multi", "value1")
        headers.add("X-Multi", "value2")
        mock_response.headers = headers
        result = Urllib3HTTPResult(
            status_code=200, reason="OK", response=mock_response
        )
        self.assertEqual(result.headers()["X-Multi"], "value1, value2")


# pylint: disable=protected-access,no-self-use
class TestUrllib3HTTPTransport(unittest.TestCase):
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
                    transport = Urllib3HTTPTransport()
                    result = transport.request("POST", _TEST_URL)
                    self.assertEqual(result.status_code, status_code)
                    self.assertEqual(result.reason, reason)
                    self.assertIsNone(result.error)

    @mocketize
    def test_request_returns_response_content(self):
        Entry.single_register(Entry.POST, _TEST_URL, status=200)
        transport = Urllib3HTTPTransport()
        result = transport.request("POST", _TEST_URL)
        self.assertIsInstance(result.content(), bytes)

    @mocketize
    def test_request_forwards_headers(self):
        headers = {
            "content-type": "application/x-protobuf",
            "x-custom": "value",
        }
        Entry.single_register(Entry.POST, _TEST_URL, status=200)
        transport = Urllib3HTTPTransport()
        result = transport.request("POST", _TEST_URL, headers=headers)
        self.assertEqual(result.status_code, 200)
        req = Mocket.last_request()
        for key, value in headers.items():
            self.assertEqual(req.headers[key], value)

    @mocketize
    def test_request_forwards_data(self):
        Entry.single_register(Entry.POST, _TEST_URL, status=200)
        transport = Urllib3HTTPTransport()
        result = transport.request("POST", _TEST_URL, data=b"payload")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(Mocket.last_request().body, "payload")

    def test_request_catches_exception(self):
        cases = [
            (RuntimeError("unexpected"), False),
            (urllib3.exceptions.ProtocolError("failed"), True),
        ]
        for error, expected_is_connection_error in cases:
            with self.subTest(error_type=type(error).__name__):
                transport = Urllib3HTTPTransport()
                with patch.object(
                    transport._pool, "request", side_effect=error
                ):
                    result = transport.request("POST", _TEST_URL)
                self.assertIsNone(result.status_code)
                self.assertIsNone(result.reason)
                self.assertIs(result.error, error)
                self.assertEqual(
                    transport.is_connection_error(result.error),
                    expected_is_connection_error,
                )

    def test_is_connection_error(self):
        cases: list[tuple[Exception | None, bool]] = [
            (urllib3.exceptions.ProtocolError("error"), True),
            (urllib3.exceptions.NewConnectionError(None, "error"), True),
            (urllib3.exceptions.ConnectTimeoutError(None, "error"), True),
            (urllib3.exceptions.MaxRetryError(None, "http://x"), True),
            (urllib3.exceptions.HTTPError("error"), False),
            (
                urllib3.exceptions.ReadTimeoutError(
                    None, "http://x", "timeout"
                ),
                False,
            ),
            (RuntimeError("error"), False),
            (ValueError("error"), False),
            (None, False),
        ]
        name_resolution_error = getattr(
            urllib3.exceptions, "NameResolutionError", None
        )
        if name_resolution_error is not None:
            cases.append((name_resolution_error("host", None, "error"), True))
        transport = Urllib3HTTPTransport()
        for exception, expected in cases:
            with self.subTest(error_type=type(exception).__name__):
                self.assertEqual(
                    transport.is_connection_error(exception), expected
                )

    def test_request_passes_timeout(self):
        cases = [
            3.5,
            None,
        ]
        for timeout in cases:
            with self.subTest(timeout=timeout):
                transport = Urllib3HTTPTransport()
                with patch.object(transport._pool, "request") as mock_request:
                    mock_request.return_value = MagicMock(
                        status=200, reason="OK"
                    )
                    transport.request("POST", _TEST_URL, timeout=timeout)
                timeout_kwarg = mock_request.call_args.kwargs["timeout"]
                if timeout is not None:
                    self.assertIsInstance(timeout_kwarg, urllib3.Timeout)
                    self.assertEqual(timeout_kwarg.total, timeout)
                else:
                    self.assertIsNone(timeout_kwarg)

    def test_verify_sets_pool_manager_kwargs(self):
        cases = [
            (True, "CERT_REQUIRED", None),
            (False, "CERT_NONE", None),
            ("/path/to/ca.pem", "CERT_REQUIRED", "/path/to/ca.pem"),
        ]
        for verify, expected_cert_reqs, expected_ca_certs in cases:
            with self.subTest(verify=verify):
                with patch("urllib3.PoolManager") as mock_pm:
                    Urllib3HTTPTransport(verify=verify)
                kwargs = mock_pm.call_args.kwargs
                self.assertEqual(kwargs["cert_reqs"], expected_cert_reqs)
                if expected_ca_certs is not None:
                    self.assertEqual(kwargs["ca_certs"], expected_ca_certs)
                else:
                    self.assertNotIn("ca_certs", kwargs)

    def test_cert_none_does_not_set_cert_file(self):
        with patch("urllib3.PoolManager") as mock_pm:
            Urllib3HTTPTransport(cert=None)
        self.assertNotIn("cert_file", mock_pm.call_args.kwargs)

    def test_cert_sets_pool_manager_kwargs(self):
        cases = [
            ("/path/to/cert.pem", "/path/to/cert.pem", None),
            (
                ("/path/to/cert.pem", "/path/to/key.pem"),
                "/path/to/cert.pem",
                "/path/to/key.pem",
            ),
        ]
        for cert, expected_cert_file, expected_key_file in cases:
            with self.subTest(cert=cert):
                with patch("urllib3.PoolManager") as mock_pm:
                    Urllib3HTTPTransport(cert=cert)
                kwargs = mock_pm.call_args.kwargs
                self.assertEqual(kwargs["cert_file"], expected_cert_file)
                if expected_key_file is not None:
                    self.assertEqual(kwargs["key_file"], expected_key_file)
                else:
                    self.assertNotIn("key_file", kwargs)

    def test_retries_disabled(self):
        with patch("urllib3.PoolManager") as mock_pm:
            Urllib3HTTPTransport()
        retries = mock_pm.call_args.kwargs["retries"]
        self.assertIsInstance(retries, urllib3.Retry)
        self.assertEqual(retries.total, 0)
        self.assertFalse(retries.redirect)

    def test_close_clears_pool(self):
        with patch("urllib3.PoolManager") as mock_pm:
            transport = Urllib3HTTPTransport()
            transport.close()
        mock_pm.return_value.clear.assert_called_once()
