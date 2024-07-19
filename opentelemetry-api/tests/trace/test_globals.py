import unittest
from unittest.mock import Mock, patch

from opentelemetry import context, trace
from opentelemetry.test.concurrency_test import ConcurrencyTestBase, MockFunc
from opentelemetry.test.globals_test import TraceGlobalsTest
from opentelemetry.trace.status import Status, StatusCode


class SpanTest(trace.NonRecordingSpan):
    has_ended = False
    recorded_exception = None
    recorded_status = Status(status_code=StatusCode.UNSET)

    def set_status(self, status, description=None):
        self.recorded_status = status

    def end(self, end_time=None):
        self.has_ended = True

    def is_recording(self):
        return not self.has_ended

    def record_exception(
        self, exception, attributes=None, timestamp=None, escaped=False
    ):
        self.recorded_exception = exception


class TestGlobals(TraceGlobalsTest, unittest.TestCase):
    @staticmethod
    @patch("opentelemetry.trace._TRACER_PROVIDER")
    def test_get_tracer(mock_tracer_provider):  # type: ignore
        """trace.get_tracer should proxy to the global tracer provider."""
        trace.get_tracer("foo", "var")
        mock_tracer_provider.get_tracer.assert_called_with(
            "foo", "var", None, None
        )
        mock_provider = Mock()
        trace.get_tracer("foo", "var", mock_provider)
        mock_provider.get_tracer.assert_called_with("foo", "var", None, None)


class TestGlobalsConcurrency(TraceGlobalsTest, ConcurrencyTestBase):
    @patch("opentelemetry.trace.logger")
    def test_set_tracer_provider_many_threads(self, mock_logger) -> None:  # type: ignore
        mock_logger.warning = MockFunc()

        def do_concurrently() -> Mock:
            # first get a proxy tracer
            proxy_tracer = trace.ProxyTracerProvider().get_tracer("foo")

            # try to set the global tracer provider
            mock_tracer_provider = Mock(get_tracer=MockFunc())
            trace.set_tracer_provider(mock_tracer_provider)

            # start a span through the proxy which will call through to the mock provider
            proxy_tracer.start_span("foo")

            return mock_tracer_provider

        num_threads = 100
        mock_tracer_providers = self.run_with_many_threads(
            do_concurrently,
            num_threads=num_threads,
        )

        # despite trying to set tracer provider many times, only one of the
        # mock_tracer_providers should have stuck and been called from
        # proxy_tracer.start_span()
        mock_tps_with_any_call = [
            mock
            for mock in mock_tracer_providers
            if mock.get_tracer.call_count > 0
        ]

        self.assertEqual(len(mock_tps_with_any_call), 1)
        self.assertEqual(
            mock_tps_with_any_call[0].get_tracer.call_count, num_threads
        )

        # should have warned every time except for the successful set
        self.assertEqual(mock_logger.warning.call_count, num_threads - 1)


class TestTracer(unittest.TestCase):
    def setUp(self):
        self.tracer = trace.NoOpTracer()

    def test_get_current_span(self):
        """NoOpTracer's start_span will also
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

        test_span = SpanTest(trace.INVALID_SPAN_CONTEXT)

        with trace.use_span(test_span):
            pass
        self.assertFalse(test_span.has_ended)

        with trace.use_span(test_span, end_on_exit=True):
            pass
        self.assertTrue(test_span.has_ended)

    def test_use_span_exception(self):
        class TestUseSpanException(Exception):
            pass

        test_span = SpanTest(trace.INVALID_SPAN_CONTEXT)
        exception = TestUseSpanException("test exception")
        with self.assertRaises(TestUseSpanException):
            with trace.use_span(test_span):
                raise exception

        self.assertEqual(test_span.recorded_exception, exception)

    def test_use_span_set_status(self):
        class TestUseSpanException(Exception):
            pass

        test_span = SpanTest(trace.INVALID_SPAN_CONTEXT)
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
