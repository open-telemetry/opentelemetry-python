# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
# pylint: disable=import-error

import unittest
from unittest.mock import MagicMock, patch

from opentelemetry.exporter.http.transport import _load_http_transport_factory
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
        self.assertIs(
            _load_http_transport_factory("requests"), RequestsHTTPTransport
        )

    def test_returns_urllib3_transport(self):
        self.assertIs(
            _load_http_transport_factory("urllib3"), Urllib3HTTPTransport
        )

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
            self.assertRaises(
                ValueError, _load_http_transport_factory, "nonexistent"
            )
