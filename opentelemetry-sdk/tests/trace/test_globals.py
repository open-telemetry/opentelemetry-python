# type:ignore
import unittest
from logging import WARNING

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider  # type:ignore


class TestGlobals(unittest.TestCase):
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
