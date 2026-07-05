# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access

import os
import unittest
from logging import WARNING
from unittest.mock import patch

import requests

from opentelemetry.exporter.http.transport._requests import (
    RequestsHTTPTransport,
)
from opentelemetry.exporter.http.transport._urllib3 import (
    Urllib3HTTPTransport,
)
from opentelemetry.exporter.otlp.common import _http
from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http._common import (
    _DEFAULT_TIMEOUT,
    _build_transport,
    _normalize_compression,
    _resolve_compression,
    _resolve_endpoint,
    _resolve_headers,
    _resolve_timeout,
)
from opentelemetry.exporter.otlp.proto.http.version import __version__
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_TIMEOUT,
    OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
    OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
    OTEL_EXPORTER_OTLP_TRACES_ENDPOINT,
    OTEL_EXPORTER_OTLP_TRACES_HEADERS,
    OTEL_EXPORTER_OTLP_TRACES_TIMEOUT,
)

_USER_AGENT = "OTel-OTLP-Exporter-Python/" + __version__
_BASE_HEADERS = {
    "content-type": "application/x-protobuf",
    "user-agent": _USER_AGENT,
}


class TestResolveCommon(unittest.TestCase):
    def test_resolve_endpoint(self):
        cases = [
            # per-signal wins over base and is returned verbatim (no path added)
            (
                "per_signal_verbatim",
                {
                    OTEL_EXPORTER_OTLP_TRACES_ENDPOINT: "http://per-signal:4318/v1/traces",
                    OTEL_EXPORTER_OTLP_ENDPOINT: "http://base:4318",
                },
                "v1/traces",
                "http://per-signal:4318/v1/traces",
            ),
            (
                "base_no_trailing_slash",
                {OTEL_EXPORTER_OTLP_ENDPOINT: "http://base:4318"},
                "v1/traces",
                "http://base:4318/v1/traces",
            ),
            (
                "base_trailing_slash_normalized",
                {OTEL_EXPORTER_OTLP_ENDPOINT: "http://base:4318/"},
                "v1/metrics",
                "http://base:4318/v1/metrics",
            ),
            (
                "empty_per_signal_falls_back",
                {
                    OTEL_EXPORTER_OTLP_ENDPOINT: "http://base:4318",
                    OTEL_EXPORTER_OTLP_TRACES_ENDPOINT: "",
                },
                "v1/traces",
                "http://base:4318/v1/traces",
            ),
            (
                "empty_base_falls_back_to_default",
                {OTEL_EXPORTER_OTLP_ENDPOINT: ""},
                "v1/traces",
                "http://localhost:4318/v1/traces",
            ),
            (
                "default_traces",
                {},
                "v1/traces",
                "http://localhost:4318/v1/traces",
            ),
            (
                "default_logs",
                {},
                "v1/logs",
                "http://localhost:4318/v1/logs",
            ),
        ]
        for label, env, default_path, expected in cases:
            with self.subTest(label), patch.dict(os.environ, env, clear=True):
                self.assertEqual(
                    _resolve_endpoint(
                        OTEL_EXPORTER_OTLP_TRACES_ENDPOINT, default_path
                    ),
                    expected,
                )

    def test_resolve_headers(self):
        cases = [
            ("defaults_only", {}, None, _BASE_HEADERS),
            (
                "general_env_merged",
                {OTEL_EXPORTER_OTLP_HEADERS: "k1=v1,k2=v2"},
                None,
                {**_BASE_HEADERS, "k1": "v1", "k2": "v2"},
            ),
            # per-signal var is used instead of (not merged with) the general one
            (
                "per_signal_overrides_general",
                {
                    OTEL_EXPORTER_OTLP_HEADERS: "api-key=general,shared=g",
                    OTEL_EXPORTER_OTLP_TRACES_HEADERS: "api-key=per-signal",
                },
                None,
                {**_BASE_HEADERS, "api-key": "per-signal"},
            ),
            # empty per-signal var falls back to (inherits) the general one
            (
                "empty_per_signal_falls_back_to_general",
                {
                    OTEL_EXPORTER_OTLP_HEADERS: "api-key=general",
                    OTEL_EXPORTER_OTLP_TRACES_HEADERS: "",
                },
                None,
                {**_BASE_HEADERS, "api-key": "general"},
            ),
            # explicit arg wins over env and base, by exact key
            (
                "explicit_arg_overrides",
                {OTEL_EXPORTER_OTLP_HEADERS: "api-key=from-env"},
                {"api-key": "explicit", "Content-Type": "text/plain"},
                {
                    "content-type": "text/plain",
                    "user-agent": _USER_AGENT,
                    "api-key": "explicit",
                },
            ),
            # env override of a default header must replace it
            (
                "env_overrides_default_header_case_insensitively",
                {OTEL_EXPORTER_OTLP_HEADERS: "user-agent=custom-agent"},
                None,
                {
                    "content-type": "application/x-protobuf",
                    "user-agent": "custom-agent",
                },
            ),
            (
                "explicit_arg_overrides_default_header_case_insensitively",
                {},
                {"User-Agent": "explicit-agent"},
                {
                    "content-type": "application/x-protobuf",
                    "user-agent": "explicit-agent",
                },
            ),
        ]
        for label, env, headers_arg, expected in cases:
            with self.subTest(label), patch.dict(os.environ, env, clear=True):
                self.assertEqual(
                    _resolve_headers(
                        headers_arg, OTEL_EXPORTER_OTLP_TRACES_HEADERS
                    ),
                    expected,
                )

    def test_resolve_timeout(self):
        cases = [
            (
                "per_signal_wins",
                {
                    OTEL_EXPORTER_OTLP_TRACES_TIMEOUT: "5",
                    OTEL_EXPORTER_OTLP_TIMEOUT: "7",
                },
                5.0,
                False,
            ),
            (
                "falls_back_to_general",
                {OTEL_EXPORTER_OTLP_TIMEOUT: "7"},
                7.0,
                False,
            ),
            (
                "fractional",
                {OTEL_EXPORTER_OTLP_TRACES_TIMEOUT: "2.5"},
                2.5,
                False,
            ),
            ("default", {}, float(_DEFAULT_TIMEOUT), False),
            (
                "empty_per_signal_falls_back_to_general",
                {
                    OTEL_EXPORTER_OTLP_TRACES_TIMEOUT: "",
                    OTEL_EXPORTER_OTLP_TIMEOUT: "7",
                },
                7.0,
                False,
            ),
            (
                "empty_falls_back_to_default",
                {OTEL_EXPORTER_OTLP_TRACES_TIMEOUT: ""},
                float(_DEFAULT_TIMEOUT),
                False,
            ),
            (
                "invalid_value_logs_and_defaults",
                {OTEL_EXPORTER_OTLP_TRACES_TIMEOUT: "not-a-number"},
                float(_DEFAULT_TIMEOUT),
                True,
            ),
        ]
        for label, env, expected, errors in cases:
            with self.subTest(label), patch.dict(os.environ, env, clear=True):
                if errors:
                    with self.assertLogs(level=WARNING):
                        result = _resolve_timeout(
                            OTEL_EXPORTER_OTLP_TRACES_TIMEOUT
                        )
                else:
                    result = _resolve_timeout(
                        OTEL_EXPORTER_OTLP_TRACES_TIMEOUT
                    )
                self.assertEqual(result, expected)
                self.assertIsInstance(result, float)

    def test_resolve_compression(self):
        cases = [
            (
                "gzip",
                {OTEL_EXPORTER_OTLP_TRACES_COMPRESSION: "gzip"},
                _http.Compression.GZIP,
                False,
            ),
            (
                "deflate",
                {OTEL_EXPORTER_OTLP_TRACES_COMPRESSION: "deflate"},
                _http.Compression.DEFLATE,
                False,
            ),
            (
                "none",
                {OTEL_EXPORTER_OTLP_TRACES_COMPRESSION: "none"},
                _http.Compression.NONE,
                False,
            ),
            (
                "case_and_whitespace",
                {OTEL_EXPORTER_OTLP_TRACES_COMPRESSION: "  GzIp  "},
                _http.Compression.GZIP,
                False,
            ),
            (
                "falls_back_to_general",
                {OTEL_EXPORTER_OTLP_COMPRESSION: "deflate"},
                _http.Compression.DEFLATE,
                False,
            ),
            (
                "per_signal_wins",
                {
                    OTEL_EXPORTER_OTLP_TRACES_COMPRESSION: "gzip",
                    OTEL_EXPORTER_OTLP_COMPRESSION: "deflate",
                },
                _http.Compression.GZIP,
                False,
            ),
            (
                "empty_per_signal_falls_back_to_general",
                {
                    OTEL_EXPORTER_OTLP_TRACES_COMPRESSION: "",
                    OTEL_EXPORTER_OTLP_COMPRESSION: "gzip",
                },
                _http.Compression.GZIP,
                False,
            ),
            ("default", {}, _http.Compression.NONE, False),
            (
                "invalid_warns",
                {OTEL_EXPORTER_OTLP_TRACES_COMPRESSION: "bogus"},
                _http.Compression.NONE,
                True,
            ),
        ]
        for label, env, expected, warns in cases:
            with self.subTest(label), patch.dict(os.environ, env, clear=True):
                if warns:
                    with self.assertLogs(level=WARNING):
                        result = _resolve_compression(
                            OTEL_EXPORTER_OTLP_TRACES_COMPRESSION
                        )
                else:
                    result = _resolve_compression(
                        OTEL_EXPORTER_OTLP_TRACES_COMPRESSION
                    )
                self.assertEqual(result, expected)

    def test_normalize_compression(self):
        cases = [
            ("none_passthrough", None, None),
            (
                "legacy_no_compression",
                Compression.NoCompression,
                _http.Compression.NONE,
            ),
            ("legacy_deflate", Compression.Deflate, _http.Compression.DEFLATE),
            ("legacy_gzip", Compression.Gzip, _http.Compression.GZIP),
            (
                "common_passthrough_none",
                _http.Compression.NONE,
                _http.Compression.NONE,
            ),
            (
                "common_passthrough_deflate",
                _http.Compression.DEFLATE,
                _http.Compression.DEFLATE,
            ),
            (
                "common_passthrough_gzip",
                _http.Compression.GZIP,
                _http.Compression.GZIP,
            ),
        ]
        for label, given, expected in cases:
            with self.subTest(label):
                self.assertEqual(_normalize_compression(given), expected)


class TestBuildTransport(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_default_transport_is_urllib3(self):
        result = _build_transport(
            None,
            None,
            None,
            OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
            OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
            OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
            session=None,
        )
        self.assertIsInstance(result, Urllib3HTTPTransport)

    @patch.dict(os.environ, {}, clear=True)
    def test_session_forces_requests_transport(self):
        session = requests.Session()
        result = _build_transport(
            None,
            None,
            None,
            OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
            OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
            OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
            session=session,
        )
        self.assertIsInstance(result, RequestsHTTPTransport)
        # pylint: disable-next=protected-access
        self.assertIs(result._session, session)

    def test_build_transport_verify_and_cert(self):
        cases = [
            (
                "explicit_args_win",
                {
                    OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE: "env-cert.pem",
                    OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY: "env-key.pem",
                    OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE: "env-cert2.pem",
                },
                "arg-cert.pem",
                "arg-key.pem",
                "arg-cert2.pem",
                "arg-cert.pem",
                ("arg-cert2.pem", "arg-key.pem"),
            ),
            (
                "per_signal_env_wins_over_general",
                {
                    OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE: "per-signal-cert.pem",
                    OTEL_EXPORTER_OTLP_CERTIFICATE: "general-cert.pem",
                    OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY: "per-signal-key.pem",
                    OTEL_EXPORTER_OTLP_CLIENT_KEY: "general-key.pem",
                    OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE: "per-signal-cert2.pem",
                    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE: "general-cert2.pem",
                },
                None,
                None,
                None,
                "per-signal-cert.pem",
                ("per-signal-cert2.pem", "per-signal-key.pem"),
            ),
            (
                "falls_back_to_general_env",
                {
                    OTEL_EXPORTER_OTLP_CERTIFICATE: "general-cert.pem",
                    OTEL_EXPORTER_OTLP_CLIENT_KEY: "general-key.pem",
                    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE: "general-cert2.pem",
                },
                None,
                None,
                None,
                "general-cert.pem",
                ("general-cert2.pem", "general-key.pem"),
            ),
            (
                "empty_certificate_at_every_level_falls_back_to_default_true",
                {
                    OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE: "",
                    OTEL_EXPORTER_OTLP_CERTIFICATE: "",
                },
                None,
                None,
                None,
                True,
                None,
            ),
            (
                "defaults_verify_true_no_cert",
                {},
                None,
                None,
                None,
                True,
                None,
            ),
            (
                "only_cert_file_not_tupled",
                {
                    OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE: "cert2.pem",
                },
                None,
                None,
                None,
                True,
                "cert2.pem",
            ),
            (
                "explicit_false_disables_verification_over_env",
                {
                    OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE: "env-cert.pem",
                    OTEL_EXPORTER_OTLP_CERTIFICATE: "general-cert.pem",
                },
                False,
                None,
                None,
                False,
                None,
            ),
        ]
        for (
            label,
            env,
            certificate_file,
            client_key_file,
            client_certificate_file,
            expected_verify,
            expected_cert,
        ) in cases:
            with self.subTest(label), patch.dict(os.environ, env, clear=True):
                with patch(
                    "opentelemetry.exporter.otlp.proto.http._common.Urllib3HTTPTransport"
                ) as mock_transport:
                    result = _build_transport(
                        certificate_file,
                        client_key_file,
                        client_certificate_file,
                        OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
                        OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
                        OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
                        session=None,
                    )
                mock_transport.assert_called_once_with(
                    verify=expected_verify, cert=expected_cert
                )
                self.assertIs(result, mock_transport.return_value)

    def test_build_transport_passes_verify_and_cert_to_requests(self):
        session = requests.Session()
        with (
            patch.dict(
                os.environ,
                {OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE: "cert.pem"},
                clear=True,
            ),
            patch(
                "opentelemetry.exporter.otlp.proto.http._common.RequestsHTTPTransport"
            ) as mock_transport,
        ):
            result = _build_transport(
                None,
                None,
                None,
                OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
                OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
                OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
                session=session,
            )
        mock_transport.assert_called_once_with(
            verify="cert.pem", cert=None, session=session
        )
        self.assertIs(result, mock_transport.return_value)
