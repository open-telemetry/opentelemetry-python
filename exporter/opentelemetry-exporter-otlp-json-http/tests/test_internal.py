# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access

import os
import unittest
from logging import WARNING
from unittest.mock import MagicMock, patch

from opentelemetry.exporter.http.transport._urllib3 import Urllib3HTTPTransport
from opentelemetry.exporter.otlp.common.http import Compression
from opentelemetry.exporter.otlp.json.http._internal import (
    _DEFAULT_TIMEOUT,
    _build_transport,
    _resolve_compression,
    _resolve_endpoint,
    _resolve_headers,
    _resolve_timeout,
)
from opentelemetry.exporter.otlp.json.http.version import __version__
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

_USER_AGENT = "OTel-OTLP-JSON-Exporter-Python/" + __version__
_BASE_HEADERS = {"content-type": "application/json", "user-agent": _USER_AGENT}


class TestResolveInternal(unittest.TestCase):
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
                {
                    OTEL_EXPORTER_OTLP_ENDPOINT: "",
                },
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
                    "content-type": "application/json",
                    "user-agent": "custom-agent",
                },
            ),
            (
                "explicit_arg_overrides_default_header_case_insensitively",
                {},
                {"User-Agent": "explicit-agent"},
                {
                    "content-type": "application/json",
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
            ("gzip", {"COMP": "gzip"}, "COMP", Compression.GZIP, False),
            (
                "deflate",
                {"COMP": "deflate"},
                "COMP",
                Compression.DEFLATE,
                False,
            ),
            ("none", {"COMP": "none"}, "COMP", Compression.NONE, False),
            (
                "case_and_whitespace",
                {"COMP": "  GzIp  "},
                "COMP",
                Compression.GZIP,
                False,
            ),
            (
                "falls_back_to_general",
                {OTEL_EXPORTER_OTLP_COMPRESSION: "deflate"},
                OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
                Compression.DEFLATE,
                False,
            ),
            (
                "per_signal_wins",
                {
                    OTEL_EXPORTER_OTLP_TRACES_COMPRESSION: "gzip",
                    OTEL_EXPORTER_OTLP_COMPRESSION: "deflate",
                },
                OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
                Compression.GZIP,
                False,
            ),
            (
                "empty_per_signal_falls_back_to_general",
                {
                    OTEL_EXPORTER_OTLP_TRACES_COMPRESSION: "",
                    OTEL_EXPORTER_OTLP_COMPRESSION: "gzip",
                },
                OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
                Compression.GZIP,
                False,
            ),
            (
                "default",
                {},
                OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
                Compression.NONE,
                False,
            ),
            (
                "invalid_warns",
                {OTEL_EXPORTER_OTLP_TRACES_COMPRESSION: "bogus"},
                OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
                Compression.NONE,
                True,
            ),
        ]
        for label, env, env_var, expected, warns in cases:
            with self.subTest(label), patch.dict(os.environ, env, clear=True):
                if warns:
                    with self.assertLogs(level=WARNING):
                        result = _resolve_compression(env_var)
                else:
                    result = _resolve_compression(env_var)
                self.assertEqual(result, expected)


class TestBuildTransport(unittest.TestCase):
    def test_default_transport_factory_is_urllib3(self):
        with patch.dict(os.environ, {}, clear=True):
            result = _build_transport(
                None,
                None,
                None,
                OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
                OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
                OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
            )
        self.assertIsInstance(result, Urllib3HTTPTransport)

    def test_build_transport(self):
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
                "empty_per_signal_certificate_falls_back_to_general",
                {
                    OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE: "",
                    OTEL_EXPORTER_OTLP_CERTIFICATE: "general-cert.pem",
                },
                None,
                None,
                None,
                "general-cert.pem",
                None,
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
                mock_factory = MagicMock()
                result = _build_transport(
                    certificate_file,
                    client_key_file,
                    client_certificate_file,
                    OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
                    OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
                    OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
                    transport_factory=mock_factory,
                )
                mock_factory.assert_called_once_with(
                    verify=expected_verify, cert=expected_cert
                )
                self.assertIs(result, mock_factory.return_value)
