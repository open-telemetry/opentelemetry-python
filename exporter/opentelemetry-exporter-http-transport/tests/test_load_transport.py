# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
# pylint: disable=import-error

import os
import sys
import unittest
from logging import WARNING
from unittest.mock import MagicMock, patch

from opentelemetry.exporter.http.transport import (
    _get_default_http_transport_factory,
    _load_http_transport_factory,
)
from opentelemetry.exporter.http.transport._requests import (
    RequestsHTTPTransport,
)
from opentelemetry.exporter.http.transport._urllib3 import (
    Urllib3HTTPTransport,
)

_ENTRY_POINTS_TARGET = "opentelemetry.util._importlib_metadata.entry_points"


# pylint: disable=no-self-use
class TestLoadHTTPTransportFactory(unittest.TestCase):
    def test_returns_requests_transport(self):
        self.assertIs(_load_http_transport_factory("requests"), RequestsHTTPTransport)

    def test_returns_urllib3_transport(self):
        self.assertIs(_load_http_transport_factory("urllib3"), Urllib3HTTPTransport)

    def test_known_transport_does_not_call_entry_points(self):
        with patch(_ENTRY_POINTS_TARGET) as mock_ep:
            _load_http_transport_factory("requests")
            _load_http_transport_factory("urllib3")
        self.assertFalse(mock_ep.called)

    def test_unknown_transport_calls_entry_points(self):
        def _custom_factory(*, verify, cert, **kwargs):
            pass

        mock_ep = MagicMock()
        mock_ep.load.return_value = _custom_factory
        with patch(_ENTRY_POINTS_TARGET, return_value=[mock_ep]) as mock_fn:
            result = _load_http_transport_factory("custom")
        self.assertEqual(
            mock_fn.call_args.kwargs,
            {"group": "opentelemetry_http_transport", "name": "custom"},
        )
        self.assertIs(result, _custom_factory)

    def test_entry_point_non_callable_raises_type_error(self):
        mock_ep = MagicMock()
        mock_ep.load.return_value = "not_callable"
        with patch(_ENTRY_POINTS_TARGET, return_value=[mock_ep]):
            self.assertRaises(TypeError, _load_http_transport_factory, "bad")

    def test_unknown_transport_raises_value_error(self):
        with patch(_ENTRY_POINTS_TARGET, return_value=[]):
            self.assertRaises(ValueError, _load_http_transport_factory, "nonexistent")


class TestGetDefaultHTTPTransportFactory(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_returns_urllib3_without_requests_env_vars(self):
        self.assertIs(_get_default_http_transport_factory(), Urllib3HTTPTransport)

    def test_returns_requests_when_requests_env_var_set(self):
        names = [
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "NO_PROXY",
            "REQUESTS_CA_BUNDLE",
            "CURL_CA_BUNDLE",
        ]
        for name in names + [name.lower() for name in names]:
            with self.subTest(name=name), patch.dict(os.environ, {name: "value"}, clear=True):
                self.assertIs(_get_default_http_transport_factory(), RequestsHTTPTransport)

    @patch.dict(os.environ, {"HTTPS_PROXY": ""}, clear=True)
    def test_ignores_empty_env_var(self):
        self.assertIs(_get_default_http_transport_factory(), Urllib3HTTPTransport)

    @patch.dict(os.environ, {"OTHER_PROXY": "http://proxy:3128"}, clear=True)
    def test_ignores_unrelated_env_var(self):
        self.assertIs(_get_default_http_transport_factory(), Urllib3HTTPTransport)

    @patch.dict(os.environ, {"HTTPS_PROXY": "http://user:secret@proxy:3128"}, clear=True)
    @patch.dict(sys.modules, {"requests": None})
    def test_warns_and_returns_urllib3_when_requests_missing(self):
        with self.assertLogs(level=WARNING) as logs:
            self.assertIs(_get_default_http_transport_factory(), Urllib3HTTPTransport)
        self.assertIn("HTTPS_PROXY", logs.output[0])
        self.assertNotIn("secret", logs.output[0])
