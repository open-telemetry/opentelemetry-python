# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
# pylint: disable=import-error

import unittest
from unittest.mock import MagicMock, patch

from opentelemetry.exporter.http.transport import _load_http_transport_class
from opentelemetry.exporter.http.transport._base import BaseHTTPTransport
from opentelemetry.exporter.http.transport._requests import (
    RequestsHTTPTransport,
)
from opentelemetry.exporter.http.transport._urllib3 import (
    Urllib3HTTPTransport,
)

_ENTRY_POINTS_TARGET = "opentelemetry.util._importlib_metadata.entry_points"


# pylint: disable=no-self-use
class TestLoadHTTPTransportClass(unittest.TestCase):
    def test_returns_requests_transport(self):
        self.assertIs(
            _load_http_transport_class("requests"), RequestsHTTPTransport
        )

    def test_returns_urllib3_transport(self):
        self.assertIs(
            _load_http_transport_class("urllib3"), Urllib3HTTPTransport
        )

    def test_known_transport_does_not_call_entry_points(self):
        with patch(_ENTRY_POINTS_TARGET) as mock_ep:
            _load_http_transport_class("requests")
            _load_http_transport_class("urllib3")
        self.assertFalse(mock_ep.called)

    def test_unknown_transport_calls_entry_points(self):
        class _CustomTransport:
            pass

        BaseHTTPTransport.register(_CustomTransport)
        mock_ep = MagicMock()
        mock_ep.load.return_value = _CustomTransport
        with patch(_ENTRY_POINTS_TARGET, return_value=[mock_ep]) as mock_fn:
            result = _load_http_transport_class("custom")
        self.assertEqual(
            mock_fn.call_args.kwargs,
            {"group": "opentelemetry_http_transport", "name": "custom"},
        )
        self.assertIs(result, _CustomTransport)

    def test_entry_point_non_subclass_raises_type_error(self):
        class _NotATransport:
            pass

        mock_ep = MagicMock()
        mock_ep.load.return_value = _NotATransport
        with patch(_ENTRY_POINTS_TARGET, return_value=[mock_ep]):
            self.assertRaises(TypeError, _load_http_transport_class, "bad")

    def test_entry_point_non_class_raises_type_error(self):
        mock_ep = MagicMock()
        mock_ep.load.return_value = object()
        with patch(_ENTRY_POINTS_TARGET, return_value=[mock_ep]):
            self.assertRaises(TypeError, _load_http_transport_class, "bad")

    def test_unknown_transport_raises_value_error(self):
        with patch(_ENTRY_POINTS_TARGET, return_value=[]):
            self.assertRaises(
                ValueError, _load_http_transport_class, "nonexistent"
            )
