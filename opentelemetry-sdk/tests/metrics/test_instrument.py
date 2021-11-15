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

from opentelemetry.sdk._metrics.aggregation import SumAggregation
from opentelemetry.sdk._metrics.instrument import _Synchronous


class Test_Synchronous(TestCase):
    def test_add(self):
        """
        Test that `_Synchronous.add` can handle multiple aggregations
        """

        synchronous = _Synchronous("synchronous", aggregation=SumAggregation)

        synchronous.add(1, {"name0": "value0"})
        synchronous.add(1, {"name1": "value1"})

        self.assertIsInstance(
            synchronous._attributes_aggregations[
                frozenset({("name0", "value0")})
            ],
            SumAggregation,
        )
        self.assertIsInstance(
            synchronous._attributes_aggregations[
                frozenset({("name1", "value1")})
            ],
            SumAggregation,
        )
