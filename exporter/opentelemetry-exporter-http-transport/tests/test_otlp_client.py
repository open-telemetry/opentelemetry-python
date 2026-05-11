# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import gzip
import threading
import unittest
import zlib
from dataclasses import dataclass
from unittest.mock import Mock, patch

from opentelemetry.exporter.http.transport._base import (
    BaseHTTPResult,
    BaseHTTPTransport,
)
from opentelemetry.exporter.http.transport._otlp_client import (
    Compression,
    OTLPHTTPClient,
)


@dataclass(frozen=True, slots=True)
class _TestHTTPResult(BaseHTTPResult):
    connection_error: bool = False

    def is_connection_error(self) -> bool:
        return self.connection_error


class _TestHTTPTransport(BaseHTTPTransport):
    def __init__(self, *results):
        self.results = list(results)
        self.requests = []
        self.closed = False

    def request(
        self,
        method,
        url,
        *,
        headers=None,
        timeout=None,
        data=None,
    ):
        self.requests.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "timeout": timeout,
                "data": data,
            }
        )
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def close(self):
        self.closed = True


class TestOTLPHTTPClient(unittest.TestCase):
    @staticmethod
    def _client(
        transport,
        *,
        timeout=5.0,
        compression=Compression.NONE,
        shutdown_event=None,
        jitter=0.0,
    ):
        return OTLPHTTPClient(
            transport=transport,
            endpoint="http://example.test/v1/traces",
            timeout=timeout,
            compression=compression,
            shutdown_event=shutdown_event or threading.Event(),
            headers={"content-type": "application/x-protobuf"},
            kind="spans",
            jitter=jitter,
        )

    def test_export_success_status_codes(self):
        cases = (
            (200, "OK"),
            (204, "No Content"),
            (302, "Found"),
        )

        for status_code, reason in cases:
            with self.subTest(status_code=status_code):
                transport = _TestHTTPTransport(
                    _TestHTTPResult(status_code=status_code, reason=reason)
                )
                client = self._client(transport)

                result = client.export(b"payload")

                self.assertTrue(result.success)
                self.assertEqual(result.status_code, status_code)
                self.assertEqual(result.reason, reason)
                self.assertIsNone(result.error)

    @patch(
        "opentelemetry.exporter.http.transport._otlp_client.time.time",
        side_effect=(100.0, 100.0, 100.0),
    )
    def test_export_request_arguments(self, mock_time):
        transport = _TestHTTPTransport(
            _TestHTTPResult(status_code=200, reason="OK")
        )
        client = self._client(transport, timeout=3.0)

        client.export(b"payload")

        self.assertEqual(len(transport.requests), 1)
        self.assertEqual(
            transport.requests[0],
            {
                "method": "POST",
                "url": "http://example.test/v1/traces",
                "headers": {"content-type": "application/x-protobuf"},
                "timeout": 3.0,
                "data": b"payload",
            },
        )
        self.assertEqual(mock_time.call_count, 3)

    def test_export_compresses_payload(self):
        cases = (
            (
                Compression.NONE,
                lambda data: data,
            ),
            (
                Compression.GZIP,
                gzip.decompress,
            ),
            (
                Compression.DEFLATE,
                zlib.decompress,
            ),
        )

        for compression, decompress in cases:
            with self.subTest(compression=compression):
                transport = _TestHTTPTransport(
                    _TestHTTPResult(status_code=200, reason="OK")
                )
                client = self._client(transport, compression=compression)

                result = client.export(b"payload")

                self.assertTrue(result.success)
                self.assertEqual(
                    decompress(transport.requests[0]["data"]), b"payload"
                )

    def test_export_retryable_status_codes(self):
        cases = (
            (408, "Request Timeout"),
            (500, "Internal Server Error"),
            (503, "Service Unavailable"),
        )

        for status_code, reason in cases:
            with self.subTest(status_code=status_code):
                shutdown_event = Mock(spec=threading.Event)
                shutdown_event.is_set.return_value = False
                shutdown_event.wait.return_value = False
                transport = _TestHTTPTransport(
                    _TestHTTPResult(
                        status_code=status_code,
                        reason=reason,
                    ),
                    _TestHTTPResult(status_code=200, reason="OK"),
                )
                client = self._client(
                    transport,
                    shutdown_event=shutdown_event,
                )

                result = client.export(b"payload")

                self.assertTrue(result.success)
                self.assertEqual(len(transport.requests), 2)
                shutdown_event.wait.assert_called_once_with(1.0)

    def test_export_connection_errors(self):
        error = RuntimeError("connection failed")
        transport = _TestHTTPTransport(
            _TestHTTPResult(error=error, connection_error=True),
            _TestHTTPResult(status_code=200, reason="OK"),
        )
        client = self._client(transport)

        result = client.export(b"payload")

        self.assertTrue(result.success)
        self.assertEqual(len(transport.requests), 2)
        self.assertAlmostEqual(transport.requests[0]["timeout"], 5.0, 2)
        self.assertLessEqual(
            transport.requests[1]["timeout"],
            transport.requests[0]["timeout"],
        )
        self.assertGreater(transport.requests[1]["timeout"], 0.0)

    def test_export_non_retryable_errors(self):
        exception = RuntimeError("request failed")
        cases = (
            (
                _TestHTTPResult(status_code=400, reason="Bad Request"),
                400,
                "Bad Request",
                None,
            ),
            (
                _TestHTTPResult(error=exception),
                None,
                None,
                exception,
            ),
            (
                exception,
                None,
                None,
                exception,
            ),
        )

        for (
            response,
            expected_status_code,
            expected_reason,
            expected_error,
        ) in cases:
            with self.subTest(response=type(response).__name__):
                transport = _TestHTTPTransport(response)
                client = self._client(transport)

                result = client.export(b"payload")

                self.assertFalse(result.success)
                self.assertEqual(result.status_code, expected_status_code)
                self.assertEqual(result.reason, expected_reason)
                self.assertIs(result.error, expected_error)

    def test_export_with_shutdown(self):
        shutdown_event = Mock(spec=threading.Event)
        shutdown_event.is_set.return_value = True
        transport = _TestHTTPTransport(
            _TestHTTPResult(status_code=503, reason="Service Unavailable")
        )
        client = self._client(transport, shutdown_event=shutdown_event)

        result = client.export(b"payload")

        self.assertFalse(result.success)
        self.assertEqual(result.status_code, 503)
        self.assertEqual(result.reason, "Service Unavailable")
        shutdown_event.wait.assert_not_called()

    def test_close_closes_transport(self):
        transport = _TestHTTPTransport()
        client = self._client(transport)

        client.close()

        self.assertTrue(transport.closed)
