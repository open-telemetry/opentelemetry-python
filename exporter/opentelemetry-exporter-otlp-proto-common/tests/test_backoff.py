import unittest

from opentelemetry.exporter.otlp.proto.common._internal import _create_exp_backoff_generator


class TestBackoffGenerator(unittest.TestCase):

    def test_exp_backoff_generator(self):
        generator = _create_exp_backoff_generator()
        self.assertEqual(next(generator), 1)
        self.assertEqual(next(generator), 2)
        self.assertEqual(next(generator), 4)
        self.assertEqual(next(generator), 8)
        self.assertEqual(next(generator), 16)

    def test_exp_backoff_generator_with_max(self):
        generator = _create_exp_backoff_generator(max_value=4)
        self.assertEqual(next(generator), 1)
        self.assertEqual(next(generator), 2)
        self.assertEqual(next(generator), 4)
        self.assertEqual(next(generator), 4)
        self.assertEqual(next(generator), 4)

    def test_exp_backoff_generator_with_odd_max(self):
        # use a max_value that's not in the set
        generator = _create_exp_backoff_generator(max_value=11)
        self.assertEqual(next(generator), 1)
        self.assertEqual(next(generator), 2)
        self.assertEqual(next(generator), 4)
        self.assertEqual(next(generator), 8)
        self.assertEqual(next(generator), 11)

