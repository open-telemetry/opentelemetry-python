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

from opentelemetry.sdk.metrics._internal.exponential.aggregation import (
    power_of_two_rounded_up,
)


class TestHistogram(TestCase):
    def test_power_of_two_rounded_up(self):

        self.assertEqual(power_of_two_rounded_up(2), 2)
        self.assertEqual(power_of_two_rounded_up(4), 4)
        self.assertEqual(power_of_two_rounded_up(8), 8)
        self.assertEqual(power_of_two_rounded_up(16), 16)
        self.assertEqual(power_of_two_rounded_up(32), 32)

        self.assertEqual(power_of_two_rounded_up(3), 4)
        self.assertEqual(power_of_two_rounded_up(5), 8)
        self.assertEqual(power_of_two_rounded_up(9), 16)
        self.assertEqual(power_of_two_rounded_up(17), 32)
        self.assertEqual(power_of_two_rounded_up(33), 64)
