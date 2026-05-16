# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import urllib3
import urllib3.exceptions
from mocket import Mocket, Mocketizer, mocketize
from mocket.mocks.mockhttp import Entry

from opentelemetry.exporter.http.transport._urllib3 import (
    Urllib3HTTPResult,
    Urllib3HTTPTransport,
)

_TEST_URL = "http://example.test/v1/traces"


class TestUrllib3HTTPResult(unittest.TestCase):
    def test_is_connection_error(self):
        cases: list[tuple[Urllib3HTTPResult, bool]] = [
            (Urllib3HTTPResult(status_code=200, reason="OK"), False),
            (
                Urllib3HTTPResult(
                    error=urllib3.exceptions.ProtocolError("error")
                ),
                True,
            ),
            (
                Urllib3HTTPResult(
                    error=urllib3.exceptions.NewConnectionError(None, "error")
                ),
                True,
            ),
            (
                Urllib3HTTPResult(
                    error=urllib3.exceptions.ConnectTimeoutError(None, "error")
                ),
                True,
            ),
            (
                Urllib3HTTPResult(
                    error=urllib3.exceptions.MaxRetryError(None, "http://x")
                ),
                True,
            ),
            (
                Urllib3HTTPResult(error=urllib3.exceptions.HTTPError("error")),
                False,
            ),
            (
                Urllib3HTTPResult(
                    error=urllib3.exceptions.ReadTimeoutError(
                        None, "http://x", "timeout"
                    )
                ),
                False,
            ),
            (Urllib3HTTPResult(error=RuntimeError("error")), False),
            (Urllib3HTTPResult(error=ValueError("error")), False),
        ]
        name_resolution_error = getattr(
            urllib3.exceptions, "NameResolutionError", None
        )
        if name_resolution_error is not None:
            cases.append(
                (
                    Urllib3HTTPResult(
                        error=name_resolution_error("host", None, "error")
                    ),
                    True,
                )
            )
        for result, expected in cases:
            with self.subTest(error_type=type(result.error).__name__):
                self.assertEqual(result.is_connection_error(), expected)


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
                    Entry.single_register(Entry.POST, _TEST_URL, status=status_code)
                    transport = Urllib3HTTPTransport()
                    result = transport.request("POST", _TEST_URL)
                    self.assertEqual(result.status_code, status_code)
                    self.assertEqual(result.reason, reason)
                    self.assertIsNone(result.error)

    @mocketize
    def test_request_result_is_not_a_connection_error(self):
        Entry.single_register(Entry.POST, _TEST_URL, status=200)
        transport = Urllib3HTTPTransport()
        result = transport.request("POST", _TEST_URL)
        self.assertFalse(result.is_connection_error())

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
                    result.is_connection_error(), expected_is_connection_error
                )

    def test_request_passes_timeout(self):
        cases = [
            (3.5,),
            (None,),
        ]
        for (timeout,) in cases:
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
