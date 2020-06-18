import unittest
from unittest.mock import patch

from opentelemetry import context, trace


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
        mock_provider = unittest.mock.Mock()
        trace.get_tracer("foo", "var", mock_provider)
        mock_provider.get_tracer.assert_called_with("foo", "var")


class TestTracer(unittest.TestCase):
    def setUp(self):
        self.tracer = trace.DefaultTracer()

    def test_get_current_span(self):
        """DefaultTracer's start_span will also
        be retrievable via get_current_span
        """
        self.assertIs(trace.get_current_span(), None)
        span = trace.DefaultSpan(trace.INVALID_SPAN_CONTEXT)
        ctx = trace.set_span_in_context(span)
        token = context.attach(ctx)
        try:
            self.assertIs(trace.get_current_span(), span)
        finally:
            context.detach(token)
        self.assertIs(trace.get_current_span(), None)
