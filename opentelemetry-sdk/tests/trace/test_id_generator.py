import unittest

from opentelemetry.sdk.trace import RandomIdGenerator


class TestIdGenerator(unittest.TestCase):

    def test_random_id_generator(self):
        import random
        random.seed(10)
        id_generator = RandomIdGenerator()
        trace_id = id_generator.generate_trace_id()
        span_id = id_generator.generate_span_id()
        self.assertNotEqual(trace_id, 164207228320579316746596838417247989971)
        self.assertNotEqual(span_id, 273610340023782072)
