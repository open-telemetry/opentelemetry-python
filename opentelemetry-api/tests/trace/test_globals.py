import unittest
from logging import WARNING
from unittest.mock import patch

from opentelemetry import context, trace
from opentelemetry.sdk.trace import TracerProvider  # type:ignore


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

    def test_tracer_provider_override_warning(self):
        """trace.set_tracer_provider should throw a warning when overridden"""
        trace.set_tracer_provider(TracerProvider())
        tracer_provider = trace.get_tracer_provider()
        with self.assertLogs(level=WARNING) as test:
            trace.set_tracer_provider(TracerProvider())
            self.assertEqual(
                test.output,
                [
                    (
                        "WARNING:opentelemetry.trace:Overriding of current "
                        "TracerProvider is not allowed"
                    )
                ],
            )
        self.assertIs(tracer_provider, trace.get_tracer_provider())


class TestTracer(unittest.TestCase):
    def setUp(self):
        self.tracer = trace.DefaultTracer()

    def test_get_current_span(self):
        """DefaultTracer's start_span will also
        be retrievable via get_current_span
        """
        self.assertEqual(trace.get_current_span(), trace.INVALID_SPAN)
        span = trace.INVALID_SPAN
        ctx = trace.set_span_in_context(span)
        token = context.attach(ctx)
        try:
            self.assertIs(trace.get_current_span(), span)
        finally:
            context.detach(token)
        self.assertEqual(trace.get_current_span(), trace.INVALID_SPAN)
