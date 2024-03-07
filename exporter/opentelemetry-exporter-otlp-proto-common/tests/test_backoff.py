# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import random
from unittest import TestCase

from opentelemetry.exporter.otlp.proto.common.exporter import (
    _create_exp_backoff_generator,
    _create_exp_backoff_with_jitter_generator,
)


class TestBackoffGenerator(TestCase):
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


class TestBackoffWithJitterGenerator(TestCase):
    def setUp(self):
        self.initial_state = random.getstate()

    def tearDown(self):
        return random.setstate(self.initial_state)

    def test_exp_backoff_with_jitter_generator(self):
        random.seed(20240220)
        generator = _create_exp_backoff_with_jitter_generator(max_value=10)
        self.assertAlmostEqual(next(generator), 0.1341603010697452)
        self.assertAlmostEqual(next(generator), 0.34773275270578097)
        self.assertAlmostEqual(next(generator), 3.6022913287022913)
        self.assertAlmostEqual(next(generator), 6.663388602254524)
        self.assertAlmostEqual(next(generator), 6.492676168164246)
