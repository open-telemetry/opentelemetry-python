import unittest
from unittest.mock import MagicMock, patch

from opentelemetry import context, trace


class TestGlobals(unittest.TestCase):
    def tearDown(self) -> None:
        trace._TRACER_PROVIDER = None  # pylint: disable=protected-access

    def test_get_tracer(self):
        """trace.get_tracer should create a proxy to the global tracer provider."""
        tracer_provider = (
            trace._TRACER_PROVIDER
        ) = MagicMock()  # pylint: disable=protected-access

        tracer = trace.get_tracer("foo", "var")

        tracer_provider.get_tracer.assert_not_called()
        self.assertIsInstance(
            tracer, trace._ProxyTracer  # pylint: disable=protected-access
        )

        tracer.start_span("one")
        tracer.start_span("two")
        tracer_provider.get_tracer.assert_called_once_with(
            instrumenting_module_name="foo",
            instrumenting_library_version="var",
        )

        tracer_provider.reset_mock()
        mock_provider = unittest.mock.Mock()
        trace.get_tracer("foo", "var", mock_provider)
        tracer_provider.get_tracer.assert_not_called()
        mock_provider.get_tracer.assert_called_with("foo", "var")

    def test_set_tracer_provider(self):
        """trace.get_tracer should update global tracer provider."""
        self.assertIsNone(
            trace._TRACER_PROVIDER,  # pylint: disable=protected-access
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
            tracer_provider1,
        )

    @patch("opentelemetry.trace._load_trace_provider")
    def test_get_tracer_provider(self, load_trace_provider_mock: "MagicMock"):  # type: ignore
        """trace.get_tracer_provider should get or create a global tracer provider."""

        # Get before set
        load_trace_provider_mock.return_value = trace.DefaultTracerProvider()

        tracer_provider = trace.get_tracer_provider()
        self.assertIsNone(
            trace._TRACER_PROVIDER  # pylint: disable=protected-access
        )
        self.assertIs(
            tracer_provider, load_trace_provider_mock.return_value,
        )
        load_trace_provider_mock.assert_called_once_with("tracer_provider")
        load_trace_provider_mock.reset_mock()

        # Set
        tracer_provider1 = trace.DefaultTracerProvider()
        trace.set_tracer_provider(tracer_provider1)
        self.assertIs(
            trace._TRACER_PROVIDER,  # pylint: disable=protected-access
            tracer_provider1,
        )

        # And get
        tracer_provider2 = trace.get_tracer_provider()
        self.assertIs(
            trace._TRACER_PROVIDER,  # pylint: disable=protected-access
            tracer_provider2,
        )
        self.assertIs(tracer_provider1, tracer_provider2)
        load_trace_provider_mock.assert_not_called()


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
        self.proxy_tracer = trace.get_tracer("foo", "var")
        self.inner_tracer = MagicMock(wraps=trace.DefaultTracer())

        tracer_provider = MagicMock(wraps=trace.DefaultTracerProvider())
        tracer_provider.get_tracer.return_value = self.inner_tracer
        trace.set_tracer_provider(tracer_provider)

    def tearDown(self) -> None:
        trace._TRACER_PROVIDER = None  # pylint: disable=protected-access

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
