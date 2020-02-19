import importlib
import unittest

from opentelemetry import trace


class TestGlobals(unittest.TestCase):
    def setUp(self):
        importlib.reload(trace)

        # this class has to be declared after the importlib
        # reload, or else it will inherit from an old
        # TracerSource, rather than the new TraceSource ABC.
        # created from reload.

        static_tracer = trace.DefaultTracer()

        class DummyTracerSource(trace.TracerSource):
            """TraceSource used for testing"""

            def get_tracer(
                self,
                instrumenting_module_name: str,
                instrumenting_library_version: str = "",
            ) -> trace.Tracer:
                # pylint:disable=no-self-use,unused-argument
                return static_tracer

        trace.set_preferred_tracer_source_implementation(
            lambda _: DummyTracerSource()
        )

    @staticmethod
    def teardown():
        importlib.reload(trace)

    def test_get_tracer(self):
        """trace.get_tracer should proxy to the global tracer source."""
        global tracer sourceA
        """
        from_global_api = trace.get_tracer("foo")
        from_tracer_api = trace.tracer_source().get_tracer("foo")
        self.assertEqual(from_global_api, from_tracer_api)
