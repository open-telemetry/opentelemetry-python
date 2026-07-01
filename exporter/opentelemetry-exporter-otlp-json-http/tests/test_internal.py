# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access

import os
import unittest
from logging import WARNING
from unittest.mock import patch

from opentelemetry.exporter.otlp.common import Compression
from opentelemetry.exporter.otlp.json.http._internal import (
    _DEFAULT_TIMEOUT,
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
    OTEL_EXPORTER_OTLP_TIMEOUT,
    OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
    OTEL_EXPORTER_OTLP_TRACES_ENDPOINT,
    OTEL_EXPORTER_OTLP_TRACES_HEADERS,
    OTEL_EXPORTER_OTLP_TRACES_TIMEOUT,
)

_USER_AGENT = "OTel-OTLP-JSON-Exporter-Python/" + __version__
_BASE_HEADERS = {"Content-Type": "application/json", "User-Agent": _USER_AGENT}


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
            # explicit arg wins over env and base, by exact key
            (
                "explicit_arg_overrides",
                {OTEL_EXPORTER_OTLP_HEADERS: "api-key=from-env"},
                {"api-key": "explicit", "Content-Type": "text/plain"},
                {
                    "Content-Type": "text/plain",
                    "User-Agent": _USER_AGENT,
                    "api-key": "explicit",
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
            ),
            (
                "falls_back_to_general",
                {OTEL_EXPORTER_OTLP_TIMEOUT: "7"},
                7.0,
            ),
            (
                "fractional",
                {OTEL_EXPORTER_OTLP_TRACES_TIMEOUT: "2.5"},
                2.5,
            ),
            ("default", {}, float(_DEFAULT_TIMEOUT)),
        ]
        for label, env, expected in cases:
            with self.subTest(label), patch.dict(os.environ, env, clear=True):
                result = _resolve_timeout(OTEL_EXPORTER_OTLP_TRACES_TIMEOUT)
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
