from unittest import TestCase

from opentelemetry.trace import DefaultTracer, get_tracer


class TestGetTracer(TestCase):
    def test_get_tracer(self):
        self.assertIsInstance(get_tracer(), DefaultTracer)
