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

from __future__ import annotations

import gzip
import unittest
import zlib
from logging import WARNING
from unittest.mock import MagicMock, patch

import urllib3

from opentelemetry.exporter.otlp.json.http import Compression
from opentelemetry.exporter.otlp.json.http._internal import (
    _DEFAULT_TIMEOUT,
    _MAX_RETRIES,
    _is_retryable,
    _OTLPHttpClient,
    _resolve_compression,
    _resolve_endpoint,
    _resolve_headers,
    _resolve_timeout,
)
from opentelemetry.exporter.otlp.json.http.version import __version__
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_LOGS_COMPRESSION,
    OTEL_EXPORTER_OTLP_LOGS_ENDPOINT,
    OTEL_EXPORTER_OTLP_LOGS_HEADERS,
    OTEL_EXPORTER_OTLP_LOGS_TIMEOUT,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)

from .helpers import CountdownEvent, _build_mock_response, mock_clock

_BODY = b"test export payload"


def _build_client(**overrides) -> _OTLPHttpClient:
    """Return an _OTLPHttpClient with sensible test defaults."""
    kwargs: dict = {
        "endpoint": "http://localhost:4318/v1/test",
        "headers": {},
        "timeout": 10.0,
        "compression": Compression.NO_COMPRESSION,
        "jitter": 0,
    }
    kwargs.update(overrides)
    return _OTLPHttpClient(**kwargs)


# pylint: disable=protected-access
class TestOTLPHttpClientExport(unittest.TestCase):
    @patch.object(urllib3.PoolManager, "request")
    def test_200_returns_true(self, mock_request):
        mock_request.return_value = _build_mock_response(200)
        self.assertTrue(_build_client().export(_BODY))

    @patch.object(urllib3.PoolManager, "request")
    def test_2xx_range_returns_true(self, mock_request):
        for status in (200, 201, 204, 299):
            with self.subTest(status=status):
                mock_request.reset_mock()
                mock_request.return_value = _build_mock_response(status)
                self.assertTrue(_build_client().export(_BODY))

    def test_compression_body_handling(self):
        cases = [
            (Compression.NO_COMPRESSION, None),
            (Compression.GZIP, gzip.decompress),
            (Compression.DEFLATE, zlib.decompress),
        ]
        for compression, decompress in cases:
            with self.subTest(compression=compression):
                captured: list[bytes] = []

                def _capture(*args, **kwargs):
                    captured.append(kwargs["body"])
                    return _build_mock_response(200)

                with patch.object(urllib3.PoolManager, "request", _capture):
                    _build_client(compression=compression).export(_BODY)

                if decompress is None:
                    self.assertEqual(captured[0], _BODY)
                else:
                    self.assertEqual(decompress(captured[0]), _BODY)

    @patch.object(urllib3.PoolManager, "request")
    def test_export_returns_false_immediately_when_shutdown(
        self, mock_request
    ):
        client = _build_client()
        client._shutdown = True
        self.assertFalse(client.export(_BODY))
        mock_request.assert_not_called()

    @patch.object(urllib3.PoolManager, "request")
    def test_non_retryable_status_single_attempt(self, mock_request):
        for status in (400, 301, 408):
            with self.subTest(status=status):
                mock_request.reset_mock()
                mock_request.return_value = _build_mock_response(status)
                with self.assertLogs(level=WARNING):
                    result = _build_client().export(_BODY)
                self.assertFalse(result)
                self.assertEqual(mock_request.call_count, 1)

    @patch.object(urllib3.PoolManager, "request")
    def test_non_retryable_generic_exception_single_attempt(
        self, mock_request
    ):
        mock_request.side_effect = Exception("boom")
        with self.assertLogs(level=WARNING):
            result = _build_client().export(_BODY)
        self.assertFalse(result)
        self.assertEqual(mock_request.call_count, 1)

    @patch.object(urllib3.PoolManager, "request")
    def test_retryable_status_is_retried(self, mock_request):
        for status in (429, 503):
            with self.subTest(status=status):
                mock_request.reset_mock()
                mock_request.return_value = _build_mock_response(status)
                with mock_clock(), self.assertLogs(level=WARNING):
                    _build_client(timeout=1.5).export(_BODY)
                self.assertGreater(mock_request.call_count, 1)

    @patch.object(urllib3.PoolManager, "request")
    def test_urllib3_timeout_error_is_retried(self, mock_request):
        mock_request.side_effect = urllib3.exceptions.TimeoutError()
        with mock_clock(), self.assertLogs(level=WARNING):
            _build_client(timeout=1.5).export(_BODY)
        self.assertGreater(mock_request.call_count, 1)

    @patch.object(urllib3.PoolManager, "request")
    def test_backoff_exceeding_deadline_stops_retries(self, mock_request):
        # timeout=1.5, jitter=0:
        #   retry 0: backoff=1.0, clock=0→1.0; retry 1: backoff=2.0, 1.0+2.0>1.5 -> exit
        mock_request.return_value = _build_mock_response(503)
        with mock_clock() as now, self.assertLogs(level=WARNING):
            result = _build_client(timeout=1.5).export(_BODY)
        self.assertFalse(result)
        self.assertEqual(mock_request.call_count, 2)
        self.assertEqual(now(), 1.0)

    @patch.object(urllib3.PoolManager, "request")
    def test_remaining_deadline_passed_to_urllib3(self, mock_request):
        # timeout=2.0: first call sees 2.0s left; after 1s backoff, second sees 1.0s
        mock_request.return_value = _build_mock_response(503)
        with mock_clock(), self.assertLogs(level=WARNING):
            _build_client(timeout=2.0).export(_BODY)
        self.assertEqual(mock_request.call_args_list[0].kwargs["timeout"], 2.0)
        self.assertEqual(mock_request.call_args_list[1].kwargs["timeout"], 1.0)

    @patch.object(urllib3.PoolManager, "request")
    def test_explicit_timeout_param_overrides_client_timeout(
        self, mock_request
    ):
        # client has timeout=10, but export() called with timeout=1.5 → same as 1.5s client
        mock_request.return_value = _build_mock_response(503)
        client = _build_client(timeout=10.0)
        with mock_clock() as now, self.assertLogs(level=WARNING):
            result = client.export(_BODY, timeout=1.5)
        self.assertFalse(result)
        self.assertEqual(mock_request.call_count, 2)
        self.assertEqual(now(), 1.0)

    @patch.object(urllib3.PoolManager, "request")
    def test_max_retries_exhausted(self, mock_request):
        # timeout=1000, jitter=0: all _MAX_RETRIES (6) attempts made.
        # Backoffs waited: 2^0+2^1+2^2+2^3+2^4 = 31s (6th exits on retry_num+1==MAX).
        mock_request.return_value = _build_mock_response(503)
        with mock_clock() as now, self.assertLogs(level=WARNING):
            result = _build_client(timeout=1000.0).export(_BODY)
        self.assertFalse(result)
        self.assertEqual(mock_request.call_count, _MAX_RETRIES)
        self.assertEqual(now(), 31.0)

    @patch.object(urllib3.PoolManager, "request")
    def test_export_exits_when_shutdown_flag_set_mid_retry(self, mock_request):
        # The exit condition checks self._shutdown after each failed request.
        # Setting the flag in the side_effect causes exit after the first attempt.
        client = _build_client(timeout=10.0)

        def _set_shutdown(*args, **kwargs):
            client._shutdown = True
            return _build_mock_response(503)

        mock_request.side_effect = _set_shutdown
        with self.assertLogs(level=WARNING):
            result = client.export(_BODY)
        self.assertFalse(result)
        self.assertEqual(mock_request.call_count, 1)

    @patch.object(urllib3.PoolManager, "request")
    def test_shutdown_interrupts_backoff(self, mock_request):
        # CountdownEvent triggers on the 2nd wait() call, breaking the retry loop
        # even with a very large timeout.
        client = _build_client(timeout=100.0)
        client._shutdown_in_progress = CountdownEvent(trigger_after=2)
        mock_request.return_value = _build_mock_response(503)
        with mock_clock(), self.assertLogs(level=WARNING):
            result = client.export(_BODY)
        self.assertFalse(result)
        self.assertEqual(mock_request.call_count, 2)

    @patch.object(urllib3.PoolManager, "request")
    def test_eventual_success_after_retryable_error(self, mock_request):
        # First attempt fails with 503; second succeeds with 200.
        mock_request.side_effect = [
            _build_mock_response(503),
            _build_mock_response(200),
        ]
        with mock_clock(), self.assertLogs(level=WARNING):
            result = _build_client(timeout=10.0).export(_BODY)
        self.assertTrue(result)
        self.assertEqual(mock_request.call_count, 2)


# pylint: disable=protected-access
class TestOTLPHttpClientShutdown(unittest.TestCase):
    def test_shutdown_sets_flag(self):
        client = _build_client()
        self.assertFalse(client._shutdown)
        client.shutdown()
        self.assertTrue(client._shutdown)

    def test_shutdown_sets_event(self):
        client = _build_client()
        self.assertFalse(client._shutdown_in_progress.is_set())
        client.shutdown()
        self.assertTrue(client._shutdown_in_progress.is_set())

    def test_shutdown_clears_http_pool(self):
        client = _build_client()
        mock_http = MagicMock()
        client._http = mock_http
        client.shutdown()
        mock_http.clear.assert_called_once()

    @patch.object(urllib3.PoolManager, "request")
    def test_shutdown_prevents_export(self, mock_request):
        client = _build_client()
        client.shutdown()
        result = client.export(_BODY)
        self.assertFalse(result)
        mock_request.assert_not_called()


# pylint: disable=protected-access
class TestGetBackoffWithJitter(unittest.TestCase):
    def test_jitter_zero_exact_powers_of_two(self):
        client = _build_client(jitter=0)
        for retry_num, expected in enumerate([1.0, 2.0, 4.0, 8.0, 16.0, 32.0]):
            with self.subTest(retry_num=retry_num):
                self.assertEqual(
                    client._get_backoff_with_jitter(retry_num), expected
                )

    def test_default_jitter_within_bounds(self):
        client = _build_client(jitter=0.2)
        for _ in range(50):
            result = client._get_backoff_with_jitter(0)
            self.assertGreaterEqual(result, 0.8)
            self.assertLessEqual(result, 1.2)

    def test_custom_jitter_within_bounds(self):
        client = _build_client(jitter=0.5)
        for _ in range(50):
            result = client._get_backoff_with_jitter(0)
            self.assertGreaterEqual(result, 0.5)
            self.assertLessEqual(result, 1.5)

    def test_backoff_increases_exponentially(self):
        client = _build_client(jitter=0)
        values = [client._get_backoff_with_jitter(n) for n in range(5)]
        for i in range(1, len(values)):
            with self.subTest(i=i):
                self.assertAlmostEqual(values[i], values[i - 1] * 2)


class TestIsRetryable(unittest.TestCase):
    def test_retryable_status_codes(self):
        for status in (429, 502, 503, 504):
            with self.subTest(status=status):
                self.assertTrue(_is_retryable(status))

    def test_non_retryable_4xx(self):
        for status in (400, 401, 403, 404, 408, 422):
            with self.subTest(status=status):
                self.assertFalse(_is_retryable(status))

    def test_non_retryable_5xx(self):
        for status in (500, 501, 505, 599):
            with self.subTest(status=status):
                self.assertFalse(_is_retryable(status))

    def test_non_retryable_3xx(self):
        for status in (301, 302, 304):
            with self.subTest(status=status):
                self.assertFalse(_is_retryable(status))

    def test_non_retryable_2xx(self):
        for status in (200, 201, 204):
            with self.subTest(status=status):
                self.assertFalse(_is_retryable(status))


class TestResolveEndpoint(unittest.TestCase):
    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_LOGS_ENDPOINT: "https://signal.endpoint/v1/logs",
            OTEL_EXPORTER_OTLP_ENDPOINT: "http://base.endpoint/",
        },
        clear=True,
    )
    def test_signal_specific_env_takes_priority(self):
        result = _resolve_endpoint(OTEL_EXPORTER_OTLP_LOGS_ENDPOINT, "v1/logs")
        self.assertEqual(result, "https://signal.endpoint/v1/logs")

    @patch.dict(
        "os.environ",
        {OTEL_EXPORTER_OTLP_ENDPOINT: "http://base.endpoint"},
        clear=True,
    )
    def test_falls_back_to_base_env(self):
        result = _resolve_endpoint(OTEL_EXPORTER_OTLP_LOGS_ENDPOINT, "v1/logs")
        self.assertEqual(result, "http://base.endpoint/v1/logs")

    @patch.dict(
        "os.environ",
        {OTEL_EXPORTER_OTLP_ENDPOINT: "http://base.endpoint/"},
        clear=True,
    )
    def test_base_env_trailing_slash_normalized(self):
        result = _resolve_endpoint(OTEL_EXPORTER_OTLP_LOGS_ENDPOINT, "v1/logs")
        self.assertEqual(result, "http://base.endpoint/v1/logs")

    @patch.dict("os.environ", {}, clear=True)
    def test_falls_back_to_default(self):
        result = _resolve_endpoint(OTEL_EXPORTER_OTLP_LOGS_ENDPOINT, "v1/logs")
        self.assertEqual(result, "http://localhost:4318/v1/logs")


class TestResolveHeaders(unittest.TestCase):
    @patch.dict("os.environ", {}, clear=True)
    def test_default_content_type_and_user_agent(self):
        result = _resolve_headers(None, OTEL_EXPORTER_OTLP_LOGS_HEADERS)
        self.assertEqual(result.get("Content-Type"), "application/json")
        self.assertEqual(
            result.get("User-Agent"),
            f"OTel-OTLP-JSON-Exporter-Python/{__version__}",
        )

    @patch.dict(
        "os.environ",
        {OTEL_EXPORTER_OTLP_LOGS_HEADERS: "x-custom=myval"},
        clear=True,
    )
    def test_env_headers_merged(self):
        result = _resolve_headers(None, OTEL_EXPORTER_OTLP_LOGS_HEADERS)
        self.assertEqual(result.get("x-custom"), "myval")

    @patch.dict(
        "os.environ",
        {OTEL_EXPORTER_OTLP_HEADERS: "x-common=commonval"},
        clear=True,
    )
    def test_common_env_fallback(self):
        result = _resolve_headers(None, OTEL_EXPORTER_OTLP_LOGS_HEADERS)
        self.assertEqual(result.get("x-common"), "commonval")

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_LOGS_HEADERS: "x-signal=signalval",
            OTEL_EXPORTER_OTLP_HEADERS: "x-common=commonval",
        },
        clear=True,
    )
    def test_signal_env_takes_priority_over_common_env(self):
        result = _resolve_headers(None, OTEL_EXPORTER_OTLP_LOGS_HEADERS)
        self.assertEqual(result.get("x-signal"), "signalval")
        self.assertNotIn("x-common", result)

    @patch.dict(
        "os.environ",
        {OTEL_EXPORTER_OTLP_LOGS_HEADERS: "x-env=envval"},
        clear=True,
    )
    def test_explicit_headers_override_env(self):
        result = _resolve_headers(
            {"x-env": "explicit"}, OTEL_EXPORTER_OTLP_LOGS_HEADERS
        )
        self.assertEqual(result["x-env"], "explicit")

    @patch.dict(
        "os.environ",
        {OTEL_EXPORTER_OTLP_LOGS_HEADERS: "badheader"},
        clear=True,
    )
    def test_malformed_env_header_logs_warning(self):
        with self.assertLogs(level=WARNING):
            _resolve_headers(None, OTEL_EXPORTER_OTLP_LOGS_HEADERS)


class TestResolveTimeout(unittest.TestCase):
    @patch.dict(
        "os.environ",
        {OTEL_EXPORTER_OTLP_LOGS_TIMEOUT: "999"},
        clear=True,
    )
    def test_explicit_timeout_returned(self):
        self.assertEqual(
            _resolve_timeout(5.0, OTEL_EXPORTER_OTLP_LOGS_TIMEOUT), 5.0
        )

    @patch.dict(
        "os.environ",
        {OTEL_EXPORTER_OTLP_LOGS_TIMEOUT: "30"},
        clear=True,
    )
    def test_signal_env_used_when_no_explicit(self):
        self.assertEqual(
            _resolve_timeout(None, OTEL_EXPORTER_OTLP_LOGS_TIMEOUT), 30.0
        )

    @patch.dict(
        "os.environ",
        {OTEL_EXPORTER_OTLP_TIMEOUT: "20"},
        clear=True,
    )
    def test_falls_back_to_common_env(self):
        self.assertEqual(
            _resolve_timeout(None, OTEL_EXPORTER_OTLP_LOGS_TIMEOUT), 20.0
        )

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_LOGS_TIMEOUT: "30",
            OTEL_EXPORTER_OTLP_TIMEOUT: "20",
        },
        clear=True,
    )
    def test_signal_env_takes_priority_over_common(self):
        self.assertEqual(
            _resolve_timeout(None, OTEL_EXPORTER_OTLP_LOGS_TIMEOUT), 30.0
        )

    @patch.dict("os.environ", {}, clear=True)
    def test_falls_back_to_default(self):
        self.assertEqual(
            _resolve_timeout(None, OTEL_EXPORTER_OTLP_LOGS_TIMEOUT),
            float(_DEFAULT_TIMEOUT),
        )


class TestResolveCompression(unittest.TestCase):
    def test_explicit_compression_ignores_env(self):
        cases = [
            (Compression.GZIP, "deflate"),
            (Compression.NO_COMPRESSION, "gzip"),
        ]
        for explicit, env_value in cases:
            with self.subTest(explicit=explicit, env_value=env_value):
                with patch.dict(
                    "os.environ",
                    {OTEL_EXPORTER_OTLP_LOGS_COMPRESSION: env_value},
                    clear=True,
                ):
                    result = _resolve_compression(
                        explicit, OTEL_EXPORTER_OTLP_LOGS_COMPRESSION
                    )
                    self.assertIs(result, explicit)

    def test_env_compression_values(self):
        cases = [
            ("gzip", Compression.GZIP),
            ("deflate", Compression.DEFLATE),
            ("none", Compression.NO_COMPRESSION),
        ]
        for env_value, expected in cases:
            with self.subTest(env_value=env_value):
                with patch.dict(
                    "os.environ",
                    {OTEL_EXPORTER_OTLP_LOGS_COMPRESSION: env_value},
                    clear=True,
                ):
                    self.assertIs(
                        _resolve_compression(
                            None, OTEL_EXPORTER_OTLP_LOGS_COMPRESSION
                        ),
                        expected,
                    )

    def test_env_compression_case_insensitive(self):
        cases = [
            ("GZIP", Compression.GZIP),
            ("  Deflate  ", Compression.DEFLATE),
        ]
        for env_value, expected in cases:
            with self.subTest(env_value=env_value):
                with patch.dict(
                    "os.environ",
                    {OTEL_EXPORTER_OTLP_LOGS_COMPRESSION: env_value},
                    clear=True,
                ):
                    self.assertIs(
                        _resolve_compression(
                            None, OTEL_EXPORTER_OTLP_LOGS_COMPRESSION
                        ),
                        expected,
                    )

    @patch.dict(
        "os.environ",
        {OTEL_EXPORTER_OTLP_COMPRESSION: "gzip"},
        clear=True,
    )
    def test_common_env_fallback(self):
        self.assertIs(
            _resolve_compression(None, OTEL_EXPORTER_OTLP_LOGS_COMPRESSION),
            Compression.GZIP,
        )

    @patch.dict(
        "os.environ",
        {
            OTEL_EXPORTER_OTLP_LOGS_COMPRESSION: "gzip",
            OTEL_EXPORTER_OTLP_COMPRESSION: "deflate",
        },
        clear=True,
    )
    def test_signal_env_takes_priority_over_common_env(self):
        self.assertIs(
            _resolve_compression(None, OTEL_EXPORTER_OTLP_LOGS_COMPRESSION),
            Compression.GZIP,
        )

    @patch.dict(
        "os.environ",
        {OTEL_EXPORTER_OTLP_LOGS_COMPRESSION: "lz4"},
        clear=True,
    )
    def test_invalid_env_warns_and_returns_no_compression(self):
        with self.assertLogs(level=WARNING):
            result = _resolve_compression(
                None, OTEL_EXPORTER_OTLP_LOGS_COMPRESSION
            )
        self.assertIs(result, Compression.NO_COMPRESSION)

    @patch.dict("os.environ", {}, clear=True)
    def test_default_no_compression(self):
        self.assertIs(
            _resolve_compression(None, OTEL_EXPORTER_OTLP_LOGS_COMPRESSION),
            Compression.NO_COMPRESSION,
        )


class TestPoolManagerConstruction(unittest.TestCase):
    @patch.object(urllib3, "PoolManager")
    def test_retries_disabled(self, MockPoolManager):
        _build_client()
        self.assertFalse(MockPoolManager.call_args.kwargs["retries"])

    @patch.object(urllib3, "PoolManager")
    def test_certificate_false_disables_cert_verification(
        self, MockPoolManager
    ):
        _build_client(certificate=False)
        self.assertEqual(
            MockPoolManager.call_args.kwargs["cert_reqs"], "CERT_NONE"
        )

    @patch.object(urllib3, "PoolManager")
    def test_certificate_path_sets_cert_file(self, MockPoolManager):
        _build_client(certificate="ca.crt")
        self.assertEqual(
            MockPoolManager.call_args.kwargs["cert_file"], "ca.crt"
        )

    @patch.object(urllib3, "PoolManager")
    def test_client_certificate_and_key_passed_through(self, MockPoolManager):
        _build_client(
            client_certificate_file="client.pem",
            client_key_file="client.key",
        )
        kwargs = MockPoolManager.call_args.kwargs
        self.assertEqual(kwargs["cert_file"], "client.pem")
        self.assertEqual(kwargs["key_file"], "client.key")

    @patch.object(urllib3, "PoolManager")
    def test_no_certificate_no_cert_reqs(self, MockPoolManager):
        _build_client()
        self.assertNotIn("cert_reqs", MockPoolManager.call_args.kwargs)
