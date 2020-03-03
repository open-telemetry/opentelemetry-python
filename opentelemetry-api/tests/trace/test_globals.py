from unittest import TestCase

from opentelemetry.trace import get_tracer, DefaultTracer


class TestGetTracer(TestCase):

    def test_get_tracer(self):
        self.assertIsInstance(get_tracer(), DefaultTracer)
