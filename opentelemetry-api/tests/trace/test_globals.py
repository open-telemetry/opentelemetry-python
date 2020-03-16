import unittest
from unittest.mock import patch

from opentelemetry import trace


class TestGlobals(unittest.TestCase):
    def setUp(self):
        self._patcher = patch("opentelemetry.trace._TRACER_PROVIDER")
        self._mock_tracer_provider = self._patcher.start()

    def tearDown(self) -> None:
        self._patcher.stop()

    def test_get_tracer(self):
        """trace.get_tracer should proxy to the global tracer provider."""
        trace.get_tracer("foo", "var")
        self._mock_tracer_provider.get_tracer.assert_called_with("foo", "var")
