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

from logging import WARNING
from unittest import TestCase
from unittest.mock import Mock

from opentelemetry.sdk._metrics._view_instrument_match import (
    _ViewInstrumentMatch,
)
from opentelemetry.sdk._metrics.measurement import Measurement
from opentelemetry.sdk._metrics.point import Metric


class Test_ViewInstrumentMatch(TestCase):
    @classmethod
    def setUpClass(cls):

        cls.mock_aggregation_instance = Mock()
        cls.mock_aggregation_class = Mock(
            return_value=cls.mock_aggregation_instance
        )
        cls.mock_resource = Mock()
        cls.mock_instrumentation_info = Mock()

    def test_consume_measurement(self):

        view_instrument_match = _ViewInstrumentMatch(
            "name",
            "unit",
            "description",
            self.mock_aggregation_class,
            self.mock_instrumentation_info,
            self.mock_resource,
            {"a", "c"},
        )

        view_instrument_match.consume_measurement(
            Measurement(value=0, attributes={"c": "d", "f": "g"})
        )
        self.assertEqual(
            view_instrument_match._attributes_aggregation,
            {frozenset([("c", "d")]): self.mock_aggregation_instance},
        )

        with self.assertLogs(level=WARNING):
            view_instrument_match.consume_measurement(
                Measurement(value=0, attributes={"w": "x", "y": "z"})
            )

        self.assertEqual(
            view_instrument_match._attributes_aggregation,
            {frozenset([("c", "d")]): self.mock_aggregation_instance},
        )

        view_instrument_match = _ViewInstrumentMatch(
            "name",
            "unit",
            "description",
            self.mock_aggregation_class,
            self.mock_instrumentation_info,
            self.mock_resource,
        )

        view_instrument_match.consume_measurement(
            Measurement(value=0, attributes={"c": "d", "f": "g"})
        )
        self.assertEqual(
            view_instrument_match._attributes_aggregation,
            {
                frozenset(
                    [("c", "d"), ("f", "g")]
                ): self.mock_aggregation_instance
            },
        )

    def test_collect(self):

        view_instrument_match = _ViewInstrumentMatch(
            "name",
            "unit",
            "description",
            self.mock_aggregation_class,
            self.mock_instrumentation_info,
            self.mock_resource,
            {"a", "c"},
        )

        view_instrument_match.consume_measurement(
            Measurement(value=0, attributes={"c": "d", "f": "g"})
        )
        self.assertEqual(
            next(view_instrument_match.collect(1)),
            Metric(
                attributes={"c": "d"},
                description="description",
                instrumentation_info=self.mock_instrumentation_info,
                name="name",
                resource=self.mock_resource,
                unit="unit",
                point=None,
            ),
        )
