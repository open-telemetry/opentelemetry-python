import unittest
from unittest.mock import MagicMock, patch

from opentelemetry import context, trace


class TestGlobals(unittest.TestCase):
    def setUp(self):
        self._patcher = patch("opentelemetry.trace._TRACER_PROVIDER")
        self._mock_tracer_provider = self._patcher.start()

    def tearDown(self) -> None:
        self._patcher.stop()

    def test_get_tracer(self):
        """trace.get_tracer should create a proxy to the global tracer provider."""
        tracer = trace.get_tracer("foo", "var")
        self._mock_tracer_provider.get_tracer.assert_not_called()
        self.assertIsInstance(tracer, trace._ProxyTracer)

        tracer.start_span("one")
        tracer.start_span("two")
        self._mock_tracer_provider.get_tracer.assert_called_once_with(
            instrumenting_module_name="foo",
            instrumenting_library_version="var",
        )

        mock_provider = unittest.mock.Mock()
        trace.get_tracer("foo", "var", mock_provider)
        mock_provider.get_tracer.assert_called_with("foo", "var")

    def test_set_tracer_provider(self):
        """trace.get_tracer should update global tracer provider."""
        self.assertIs(
            trace._TRACER_PROVIDER,  # pylint: disable=protected-access
            self._mock_tracer_provider,
        )

        tracer_provider1 = trace.DefaultTracerProvider()
        trace.set_tracer_provider(tracer_provider1)
        self.assertIs(
            trace._TRACER_PROVIDER,  # pylint: disable=protected-access
            tracer_provider1,
        )

        tracer_provider2 = trace.DefaultTracerProvider()
        trace.set_tracer_provider(tracer_provider2)
        self.assertIs(
            trace._TRACER_PROVIDER,  # pylint: disable=protected-access
            tracer_provider2,
        )

    @patch("opentelemetry.trace._load_trace_provider")
    def test_get_tracer_provider(self, load_trace_provider_mock: "MagicMock"):  # type: ignore
        """trace.get_tracer should get or create a global tracer provider."""
        load_trace_provider_mock.assert_not_called()

        tracer_provider = trace.get_tracer_provider()
        self.assertIs(
            trace._TRACER_PROVIDER,  # pylint: disable=protected-access
            tracer_provider,
        )
        load_trace_provider_mock.assert_not_called()

        trace._TRACER_PROVIDER = None  # pylint: disable=protected-access
        tracer_provider1 = trace.get_tracer_provider()
        self.assertIsNotNone(
            trace._TRACER_PROVIDER  # pylint: disable=protected-access
        )
        self.assertIs(
            trace._TRACER_PROVIDER,  # pylint: disable=protected-access
            tracer_provider1,
        )
        load_trace_provider_mock.assert_called_once_with("tracer_provider")

        tracer_provider2 = trace.get_tracer_provider()
        self.assertIsNotNone(
            trace._TRACER_PROVIDER  # pylint: disable=protected-access
        )
        self.assertIs(
            trace._TRACER_PROVIDER,  # pylint: disable=protected-access
            tracer_provider2,
        )
        self.assertIs(tracer_provider1, tracer_provider2)
        load_trace_provider_mock.assert_called_once_with("tracer_provider")


class TestTracer(unittest.TestCase):
    def setUp(self):
        self.tracer = trace.DefaultTracer()

    def test_get_current_span(self):
        """DefaultTracer's start_span will also
        be retrievable via get_current_span
        """
        self.assertEqual(trace.get_current_span(), trace.INVALID_SPAN)
        span = trace.DefaultSpan(trace.INVALID_SPAN_CONTEXT)
        ctx = trace.set_span_in_context(span)
        token = context.attach(ctx)
        try:
            self.assertIs(trace.get_current_span(), span)
        finally:
            context.detach(token)
        self.assertEqual(trace.get_current_span(), trace.INVALID_SPAN)


class TestProxyTracer(unittest.TestCase):
    def setUp(self):
        self._patcher = patch("opentelemetry.trace._TRACER_PROVIDER")
        self._patcher.start()

        self.proxy_tracer = trace.get_tracer("foo", "var")
        self.inner_tracer = MagicMock(wraps=trace.DefaultTracer())

        tracer_provider = MagicMock(wraps=trace.DefaultTracerProvider())
        tracer_provider.get_tracer.return_value = self.inner_tracer
        trace.set_tracer_provider(tracer_provider)

    def tearDown(self):
        self._patcher.stop()

    def test_start_span(self):
        """ProxyTracer should call `start_span` on a real `Tracer`
        """
        self.inner_tracer.start_span.assert_not_called()

        span = self.proxy_tracer.start_span("span1")
        self.assertIs(span, trace.INVALID_SPAN)
        self.inner_tracer.start_span.assert_called_once_with(
            name="span1",
            context=None,
            kind=trace.SpanKind.INTERNAL,
            attributes=None,
            links=(),
            start_time=None,
            record_exception=True,
            set_status_on_exception=True,
        )

    def test_start_as_current_span(self):
        """ProxyTracer should call `start_as_current_span` on a real `Tracer`
        """
        self.inner_tracer.start_as_current_span.assert_not_called()

        with self.proxy_tracer.start_as_current_span("span1") as span:
            self.assertIs(span, trace.INVALID_SPAN)
            self.inner_tracer.start_as_current_span.assert_called_once_with(
                name="span1",
                context=None,
                kind=trace.SpanKind.INTERNAL,
                attributes=None,
                links=(),
                start_time=None,
                record_exception=True,
                set_status_on_exception=True,
            )

        self.inner_tracer.start_as_current_span.reset_mock()

        @self.proxy_tracer.start_as_current_span("span1")
        def func(arg: str, kwarg: str) -> str:
            self.assertEqual(arg, "argval")
            self.assertEqual(kwarg, "kwargval")
            return "retval"

        self.inner_tracer.start_as_current_span.assert_not_called()

        result = func("argval", kwarg="kwargval")
        self.assertEqual(result, "retval")

        self.inner_tracer.start_as_current_span.assert_called_once_with(
            name="span1",
            context=None,
            kind=trace.SpanKind.INTERNAL,
            attributes=None,
            links=(),
            start_time=None,
            record_exception=True,
            set_status_on_exception=True,
        )

    def test_use_span(self):
        """ProxyTracer should call `use_span` on a real `Tracer`
        """
        self.inner_tracer.use_span.assert_not_called()

        span = self.proxy_tracer.start_span("span1")

        with self.proxy_tracer.use_span(span) as current_context:
            self.assertIsNone(current_context)
            self.inner_tracer.use_span.assert_called_once_with(
                span=span, end_on_exit=False,
            )

        self.inner_tracer.use_span.reset_mock()

        @self.proxy_tracer.use_span(span)
        def func(arg: str, kwarg: str) -> str:
            self.assertEqual(arg, "argval")
            self.assertEqual(kwarg, "kwargval")
            return "retval"

        self.inner_tracer.use_span.assert_not_called()

        result = func("argval", kwarg="kwargval")
        self.assertEqual(result, "retval")

        self.inner_tracer.use_span.assert_called_once_with(
            span=span, end_on_exit=False,
        )
