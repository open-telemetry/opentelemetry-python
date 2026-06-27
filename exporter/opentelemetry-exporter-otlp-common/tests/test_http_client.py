# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=unexpected-keyword-arg

import gzip
import threading
import unittest
import zlib
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import format_datetime
from unittest.mock import Mock, patch

# pylint: disable-next=import-error
from opentelemetry.exporter.http.transport._base import (
    BaseHTTPResult,
    BaseHTTPTransport,
)

# pylint: disable-next=import-error
from opentelemetry.exporter.otlp.common._http import (
    Compression,
    OTLPHTTPClient,
    _extract_retry_after,
)


@contextmanager
def _mock_clock(
    shutdown_event: Mock | None = None,
) -> Iterator[Callable[[float], None]]:
    _now = [0.0]

    def advance(delta: float) -> None:
        _now[0] += delta

    def get_time() -> float:
        return _now[0]

    if shutdown_event is not None:

        def _wait(duration: float) -> bool:
            advance(duration)
            return False

        shutdown_event.wait.side_effect = _wait

    with patch(
        "opentelemetry.exporter.otlp.common._http.time.time",
        side_effect=get_time,
    ):
        yield advance


@dataclass(frozen=True, slots=True)
class _TestHTTPResult(BaseHTTPResult):
    response_headers: dict = field(default_factory=dict)

    # pylint: disable-next=no-self-use
    def content(self) -> bytes:
        return b""

    def headers(self):
        return self.response_headers


class _TestHTTPTransport(BaseHTTPTransport):
    def __init__(self, *results, connection_errors=()):
        self.results = list(results)
        self.requests = []
        self.closed = False
        self._connection_errors = set(connection_errors)

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
        if callable(result):
            result = result()
        if isinstance(result, Exception):
            raise result
        return result

    def is_connection_error(self, exception):
        return exception in self._connection_errors

    def close(self):
        self.closed = True


class TestOTLPHTTPClient(unittest.TestCase):
    @staticmethod
    def _client(
        transport,
        *,
        timeout=5.0,
        compression=Compression.NONE,
        jitter=0.0,
    ):
        return OTLPHTTPClient(
            transport=transport,
            endpoint="http://example.test/v1/traces",
            timeout=timeout,
            compression=compression,
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
        "opentelemetry.exporter.otlp.common._http.time.time",
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
            (Compression.NONE, lambda data: data, None),
            (Compression.GZIP, gzip.decompress, "gzip"),
            (Compression.DEFLATE, zlib.decompress, "deflate"),
        )

        for compression, decompress, expected_encoding in cases:
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
                headers = transport.requests[0]["headers"]
                if expected_encoding is None:
                    self.assertNotIn("Content-Encoding", headers)
                else:
                    self.assertEqual(
                        headers["Content-Encoding"], expected_encoding
                    )

    def test_export_retryable_status_codes(self):
        cases = (
            (429, "Too Many Requests"),
            (502, "Bad Gateway"),
            (503, "Service Unavailable"),
            (504, "Gateway Timeout"),
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
                client = self._client(transport)
                # pylint: disable-next=protected-access
                client._shutdown_event = shutdown_event

                result = client.export(b"payload")

                self.assertTrue(result.success)
                self.assertEqual(len(transport.requests), 2)
                shutdown_event.wait.assert_called_once_with(1.0)

    def test_export_connection_errors(self):
        error = RuntimeError("connection failed")
        transport = _TestHTTPTransport(
            _TestHTTPResult(error=error),
            _TestHTTPResult(status_code=200, reason="OK"),
            connection_errors={error},
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
                _TestHTTPResult(status_code=408, reason="Request Timeout"),
                408,
                "Request Timeout",
                None,
            ),
            (
                _TestHTTPResult(
                    status_code=500, reason="Internal Server Error"
                ),
                500,
                "Internal Server Error",
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
        client = self._client(transport)
        # pylint: disable-next=protected-access
        client._shutdown_event = shutdown_event

        result = client.export(b"payload")

        self.assertFalse(result.success)
        self.assertEqual(result.status_code, 503)
        self.assertEqual(result.reason, "Service Unavailable")
        shutdown_event.wait.assert_not_called()

    def test_shutdown_closes_transport(self):
        transport = _TestHTTPTransport()
        client = self._client(transport)

        client.shutdown()

        self.assertTrue(transport.closed)

    def test_export_timeout_decreases_per_retry(self):
        shutdown_event = Mock(spec=threading.Event)
        shutdown_event.is_set.return_value = False
        transport = _TestHTTPTransport(
            _TestHTTPResult(status_code=503, reason="Service Unavailable"),
            _TestHTTPResult(status_code=503, reason="Service Unavailable"),
            _TestHTTPResult(status_code=200, reason="OK"),
        )
        client = self._client(transport, timeout=10.0, jitter=0.0)
        # pylint: disable-next=protected-access
        client._shutdown_event = shutdown_event

        with _mock_clock(shutdown_event):
            result = client.export(b"payload")

        # retry=0: wait(1.0) -> time=1.0, retry=1: wait(2.0) -> time=3.0, success
        self.assertTrue(result.success)
        self.assertAlmostEqual(transport.requests[0]["timeout"], 10.0)
        self.assertAlmostEqual(transport.requests[1]["timeout"], 9.0)
        self.assertAlmostEqual(transport.requests[2]["timeout"], 7.0)

    def test_export_backoff_exhausts_remaining_timeout(self):
        shutdown_event = Mock(spec=threading.Event)
        shutdown_event.is_set.return_value = False
        transport = _TestHTTPTransport(
            _TestHTTPResult(status_code=503, reason="Service Unavailable"),
            _TestHTTPResult(status_code=503, reason="Service Unavailable"),
        )
        # timeout=1.5: retry=0 backoff=1.0 fits -> wait(1.0) -> time=1.0
        # retry=1 backoff=2.0 > 0.5 remaining -> give up
        client = self._client(transport, timeout=1.5, jitter=0.0)
        # pylint: disable-next=protected-access
        client._shutdown_event = shutdown_event

        with _mock_clock(shutdown_event):
            result = client.export(b"payload")

        self.assertFalse(result.success)
        self.assertEqual(result.status_code, 503)
        self.assertEqual(len(transport.requests), 2)
        shutdown_event.wait.assert_called_once_with(1.0)

    def test_export_exhausts_max_retries(self):
        shutdown_event = Mock(spec=threading.Event)
        shutdown_event.is_set.return_value = False
        transport = _TestHTTPTransport(
            *[_TestHTTPResult(status_code=503, reason="Service Unavailable")]
            * 6
        )
        client = self._client(transport, timeout=1000.0, jitter=0.0)
        # pylint: disable-next=protected-access
        client._shutdown_event = shutdown_event

        with _mock_clock(shutdown_event):
            result = client.export(b"payload")

        self.assertFalse(result.success)
        self.assertEqual(len(transport.requests), 6)
        self.assertEqual(shutdown_event.wait.call_count, 5)
        self.assertEqual(
            [call.args[0] for call in shutdown_event.wait.call_args_list],
            [1.0, 2.0, 4.0, 8.0, 16.0],
        )

    def test_export_connection_error_gets_reduced_timeout(self):
        stale_error = RuntimeError("stale connection")
        transport = _TestHTTPTransport(
            _TestHTTPResult(status_code=200, reason="OK"),
            connection_errors={stale_error},
        )

        with _mock_clock() as advance:

            def _slow_connection_error() -> _TestHTTPResult:
                advance(2.0)
                return _TestHTTPResult(error=stale_error)

            transport.results.insert(0, _slow_connection_error)
            client = self._client(transport, timeout=5.0)
            result = client.export(b"payload")

        # _submit: deadline=0+5=5.0, after first request time=2.0, remaining=3.0
        self.assertTrue(result.success)
        self.assertEqual(len(transport.requests), 2)
        self.assertAlmostEqual(transport.requests[1]["timeout"], 3.0)

    def test_export_retry_after_header_used_as_backoff(self):
        shutdown_event = Mock(spec=threading.Event)
        shutdown_event.is_set.return_value = False
        shutdown_event.wait.return_value = False
        transport = _TestHTTPTransport(
            _TestHTTPResult(
                status_code=429,
                reason="Too Many Requests",
                response_headers={"retry-after": "5"},
            ),
            _TestHTTPResult(status_code=200, reason="OK"),
        )
        client = self._client(transport, timeout=60.0)
        # pylint: disable-next=protected-access
        client._shutdown_event = shutdown_event

        result = client.export(b"payload")

        self.assertTrue(result.success)
        self.assertEqual(len(transport.requests), 2)
        shutdown_event.wait.assert_called_once_with(5.0)

    def test_export_retry_after_header_exhausts_timeout(self):
        shutdown_event = Mock(spec=threading.Event)
        shutdown_event.is_set.return_value = False
        transport = _TestHTTPTransport(
            _TestHTTPResult(
                status_code=503,
                reason="Service Unavailable",
                response_headers={"retry-after": "10"},
            ),
        )
        client = self._client(transport, timeout=3.0, jitter=0.0)
        # pylint: disable-next=protected-access
        client._shutdown_event = shutdown_event

        with _mock_clock(shutdown_event):
            result = client.export(b"payload")

        self.assertFalse(result.success)
        self.assertEqual(result.status_code, 503)
        self.assertEqual(len(transport.requests), 1)
        shutdown_event.wait.assert_not_called()

    def test_export_retry_after_http_date(self):
        base = 1_700_000_000.0
        shutdown_event = Mock(spec=threading.Event)
        shutdown_event.is_set.return_value = False
        shutdown_event.wait.return_value = False
        retry_at = format_datetime(
            datetime.fromtimestamp(base + 30, timezone.utc), usegmt=True
        )
        transport = _TestHTTPTransport(
            _TestHTTPResult(
                status_code=503,
                reason="Service Unavailable",
                response_headers={"retry-after": retry_at},
            ),
            _TestHTTPResult(status_code=200, reason="OK"),
        )
        client = self._client(transport, timeout=120.0)
        # pylint: disable-next=protected-access
        client._shutdown_event = shutdown_event

        with patch(
            "opentelemetry.exporter.otlp.common._http.time.time",
            return_value=base,
        ):
            result = client.export(b"payload")

        self.assertTrue(result.success)
        self.assertEqual(len(transport.requests), 2)
        shutdown_event.wait.assert_called_once_with(30.0)

    def test_export_retry_after_http_date_in_past(self):
        base = 1_700_000_000.0
        shutdown_event = Mock(spec=threading.Event)
        shutdown_event.is_set.return_value = False
        shutdown_event.wait.return_value = False
        retry_at = format_datetime(
            datetime.fromtimestamp(base - 30, timezone.utc), usegmt=True
        )
        transport = _TestHTTPTransport(
            _TestHTTPResult(
                status_code=429,
                reason="Too Many Requests",
                response_headers={"retry-after": retry_at},
            ),
            _TestHTTPResult(status_code=200, reason="OK"),
        )
        client = self._client(transport, timeout=120.0)
        # pylint: disable-next=protected-access
        client._shutdown_event = shutdown_event

        with patch(
            "opentelemetry.exporter.otlp.common._http.time.time",
            return_value=base,
        ):
            result = client.export(b"payload")

        self.assertTrue(result.success)
        self.assertEqual(len(transport.requests), 2)
        shutdown_event.wait.assert_called_once_with(0.0)

    def test_export_retry_after_malformed(self):
        shutdown_event = Mock(spec=threading.Event)
        shutdown_event.is_set.return_value = False
        shutdown_event.wait.return_value = False
        transport = _TestHTTPTransport(
            _TestHTTPResult(
                status_code=503,
                reason="Service Unavailable",
                response_headers={"retry-after": "not-a-date"},
            ),
            _TestHTTPResult(status_code=200, reason="OK"),
        )
        client = self._client(transport, timeout=60.0, jitter=0.0)
        # pylint: disable-next=protected-access
        client._shutdown_event = shutdown_event

        result = client.export(b"payload")

        self.assertTrue(result.success)
        self.assertEqual(len(transport.requests), 2)
        # No usable Retry-After -> exponential backoff: 2**0 * uniform(1, 1).
        shutdown_event.wait.assert_called_once_with(1.0)

    def test_extract_retry_after_edge_cases(self):
        cases = (
            ("5", 5.0),
            ("  7  ", 7.0),
            ("-3", 0.0),
            ("nan", None),
            ("inf", None),
            ("garbage", None),
        )
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(
                    _extract_retry_after(
                        _TestHTTPResult(
                            response_headers={"retry-after": value}
                        )
                    ),
                    expected,
                )

        with self.subTest(value="absent"):
            self.assertIsNone(_extract_retry_after(_TestHTTPResult()))
