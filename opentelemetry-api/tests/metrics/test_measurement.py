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

from opentelemetry._metrics.measurement import Measurement


class TestMeasurement(TestCase):
    def test_measurement_init(self):
        try:
            # int
            Measurement(321, {"hello": "world"})

            # float
            Measurement(321.321, {"hello": "world"})
        except Exception:  # pylint: disable=broad-except
            self.fail(
                "Unexpected exception raised when instantiating Measurement"
            )

    def test_measurement_equality(self):
        self.assertEqual(
            Measurement(321, {"hello": "world"}),
            Measurement(321, {"hello": "world"}),
        )

        self.assertNotEqual(
            Measurement(321, {"hello": "world"}),
            Measurement(321.321, {"hello": "world"}),
        )
        self.assertNotEqual(
            Measurement(321, {"baz": "world"}),
            Measurement(321, {"hello": "world"}),
        )
