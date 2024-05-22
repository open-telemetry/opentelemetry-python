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

from opentelemetry.metrics import Observation


class TestObservation(TestCase):
    def test_measurement_init(self):
        try:
            # int
            Observation(321, {"hello": "world"})

            # float
            Observation(321.321, {"hello": "world"})
        except Exception:  # pylint: disable=broad-exception-caught
            self.fail(
                "Unexpected exception raised when instantiating Observation"
            )

    def test_measurement_equality(self):
        self.assertEqual(
            Observation(321, {"hello": "world"}),
            Observation(321, {"hello": "world"}),
        )

        self.assertNotEqual(
            Observation(321, {"hello": "world"}),
            Observation(321.321, {"hello": "world"}),
        )
        self.assertNotEqual(
            Observation(321, {"baz": "world"}),
            Observation(321, {"hello": "world"}),
        )
