import unittest
from unittest.mock import patch

from opentelemetry import context, trace
from opentelemetry.trace.status import Status, StatusCode


class TestSpan(trace.NonRecordingSpan):
    has_ended = False
    recorded_exception = None
    recorded_status = Status(status_code=StatusCode.UNSET)

    def set_status(self, status):
        self.recorded_status = status

    def end(self, end_time=None):
        self.has_ended = True

    def is_recording(self):
        return not self.has_ended

    def record_exception(
        self, exception, attributes=None, timestamp=None, escaped=False
    ):
        self.recorded_exception = exception


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
        # pylint: disable=protected-access
        self.tracer = trace._DefaultTracer()

    def test_get_current_span(self):
        """_DefaultTracer's start_span will also
        be retrievable via get_current_span
        """
        self.assertEqual(trace.get_current_span(), trace.INVALID_SPAN)
        span = trace.NonRecordingSpan(trace.INVALID_SPAN_CONTEXT)
        ctx = trace.set_span_in_context(span)
        token = context.attach(ctx)
        try:
            self.assertIs(trace.get_current_span(), span)
        finally:
            context.detach(token)
        self.assertEqual(trace.get_current_span(), trace.INVALID_SPAN)


class TestUseTracer(unittest.TestCase):
    def test_use_span(self):
        self.assertEqual(trace.get_current_span(), trace.INVALID_SPAN)
        span = trace.NonRecordingSpan(trace.INVALID_SPAN_CONTEXT)
        with trace.use_span(span):
            self.assertIs(trace.get_current_span(), span)
        self.assertEqual(trace.get_current_span(), trace.INVALID_SPAN)

    def test_use_span_end_on_exit(self):

        test_span = TestSpan(trace.INVALID_SPAN_CONTEXT)

        with trace.use_span(test_span):
            pass
        self.assertFalse(test_span.has_ended)

        with trace.use_span(test_span, end_on_exit=True):
            pass
        self.assertTrue(test_span.has_ended)

    def test_use_span_exception(self):
        class TestUseSpanException(Exception):
            pass

        test_span = TestSpan(trace.INVALID_SPAN_CONTEXT)
        exception = TestUseSpanException("test exception")
        with self.assertRaises(TestUseSpanException):
            with trace.use_span(test_span):
                raise exception

        self.assertEqual(test_span.recorded_exception, exception)

    def test_use_span_set_status(self):
        class TestUseSpanException(Exception):
            pass

        test_span = TestSpan(trace.INVALID_SPAN_CONTEXT)
        with self.assertRaises(TestUseSpanException):
            with trace.use_span(test_span):
                raise TestUseSpanException("test error")

        self.assertEqual(
            test_span.recorded_status.status_code, StatusCode.ERROR
        )
        self.assertEqual(
            test_span.recorded_status.description,
            "TestUseSpanException: test error",
        )
