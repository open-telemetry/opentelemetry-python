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

from unittest import TestCase

from opentelemetry.exporter.otlp.proto.common._internal import (
    _create_exp_backoff_generator,
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
