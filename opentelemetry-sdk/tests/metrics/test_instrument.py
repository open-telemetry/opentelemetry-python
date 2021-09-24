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
from unittest.mock import Mock

from opentelemetry.sdk._metrics.instrument import _ViewInstrument


class TestViewInstrument(TestCase):
    def test_instrument(self):

        view_instrument = _ViewInstrument(
            "name",
            "unit",
            "description",
            ["attribute_key_0", "attribute_key_1"],
            ["extra_dimension_0", "extra_dimension_1"],
            Mock,
            Mock(),
        )

        view_instrument.instrument(1, {})

        self.assertEqual(
            set(view_instrument._attributes_aggregation.keys()), {frozenset()}
        )

        (
            view_instrument._attributes_aggregation[
                frozenset()
            ].aggregate.assert_called_with(1)
        )
