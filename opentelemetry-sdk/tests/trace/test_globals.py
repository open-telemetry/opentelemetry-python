# type:ignore
import unittest

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider  # type:ignore


class TestGlobals(unittest.TestCase):
    def test_tracer_provider_override(self):
        """trace.set_tracer_provider should override global tracer"""
        tracer_provider = TracerProvider()
        trace.set_tracer_provider(tracer_provider)
        self.assertIs(tracer_provider, trace.get_tracer_provider())

        new_tracer_provider = TracerProvider()
        trace.set_tracer_provider(new_tracer_provider)
        self.assertIs(new_tracer_provider, trace.get_tracer_provider())
