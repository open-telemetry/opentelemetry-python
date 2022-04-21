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

from opentelemetry.sdk._metrics._view_instrument_match import (
    _ViewInstrumentMatch,
)
from opentelemetry.sdk._metrics.aggregation import (
    DropAggregation,
    _DropAggregation,
)
from opentelemetry.sdk._metrics.measurement import Measurement
from opentelemetry.sdk._metrics.point import AggregationTemporality, Metric
from opentelemetry.sdk._metrics.sdk_configuration import SdkConfiguration
from opentelemetry.sdk._metrics.view import View


class Test_ViewInstrumentMatch(TestCase):
    @classmethod
    def setUpClass(cls):

        cls.mock_aggregation_factory = Mock()
        cls.mock_created_aggregation = (
            cls.mock_aggregation_factory._create_aggregation()
        )
        cls.mock_resource = Mock()
        cls.mock_instrumentation_scope = Mock()

    def test_consume_measurement(self):
        instrument1 = Mock(name="instrument1")
        instrument1.instrumentation_scope = self.mock_instrumentation_scope
        sdk_config = SdkConfiguration(
            resource=self.mock_resource,
            metric_readers=[],
            views=[],
        )
        view_instrument_match = _ViewInstrumentMatch(
            view=View(
                instrument_name="instrument1",
                name="name",
                aggregation=self.mock_aggregation_factory,
                attribute_keys={"a", "c"},
            ),
            instrument=instrument1,
            sdk_config=sdk_config,
        )

        view_instrument_match.consume_measurement(
            Measurement(
                value=0,
                instrument=instrument1,
                attributes={"c": "d", "f": "g"},
            )
        )
        self.assertEqual(
            view_instrument_match._attributes_aggregation,
            {frozenset([("c", "d")]): self.mock_created_aggregation},
        )

        view_instrument_match.consume_measurement(
            Measurement(
                value=0,
                instrument=instrument1,
                attributes={"w": "x", "y": "z"},
            )
        )

        self.assertEqual(
            view_instrument_match._attributes_aggregation,
            {
                frozenset(): self.mock_created_aggregation,
                frozenset([("c", "d")]): self.mock_created_aggregation,
            },
        )

        # None attribute_keys (default) will keep all attributes
        view_instrument_match = _ViewInstrumentMatch(
            view=View(
                instrument_name="instrument1",
                name="name",
                aggregation=self.mock_aggregation_factory,
            ),
            instrument=instrument1,
            sdk_config=sdk_config,
        )

        view_instrument_match.consume_measurement(
            Measurement(
                value=0,
                instrument=instrument1,
                attributes={"c": "d", "f": "g"},
            )
        )
        self.assertEqual(
            view_instrument_match._attributes_aggregation,
            {
                frozenset(
                    [("c", "d"), ("f", "g")]
                ): self.mock_created_aggregation
            },
        )

        # empty set attribute_keys will drop all labels and aggregate everything together
        view_instrument_match = _ViewInstrumentMatch(
            view=View(
                instrument_name="instrument1",
                name="name",
                aggregation=self.mock_aggregation_factory,
                attribute_keys={},
            ),
            instrument=instrument1,
            sdk_config=sdk_config,
        )
        view_instrument_match.consume_measurement(
            Measurement(value=0, instrument=instrument1, attributes=None)
        )
        self.assertEqual(
            view_instrument_match._attributes_aggregation,
            {frozenset({}): self.mock_created_aggregation},
        )

        # Test that a drop aggregation is handled in the same way as any
        # other aggregation.
        drop_aggregation = DropAggregation()

        view_instrument_match = _ViewInstrumentMatch(
            view=View(
                instrument_name="instrument1",
                name="name",
                aggregation=drop_aggregation,
                attribute_keys={},
            ),
            instrument=instrument1,
            sdk_config=sdk_config,
        )
        view_instrument_match.consume_measurement(
            Measurement(value=0, instrument=instrument1, attributes=None)
        )
        self.assertIsInstance(
            view_instrument_match._attributes_aggregation[frozenset({})],
            _DropAggregation,
        )

    def test_collect(self):
        instrument1 = Mock(
            name="instrument1", description="description", unit="unit"
        )
        instrument1.instrumentation_scope = self.mock_instrumentation_scope
        sdk_config = SdkConfiguration(
            resource=self.mock_resource,
            metric_readers=[],
            views=[],
        )
        view_instrument_match = _ViewInstrumentMatch(
            view=View(
                instrument_name="instrument1",
                name="name",
                aggregation=self.mock_aggregation_factory,
                attribute_keys={"a", "c"},
            ),
            instrument=instrument1,
            sdk_config=sdk_config,
        )

        view_instrument_match.consume_measurement(
            Measurement(
                value=0,
                instrument=Mock(name="instrument1"),
                attributes={"c": "d", "f": "g"},
            )
        )
        self.assertEqual(
            next(
                view_instrument_match.collect(
                    AggregationTemporality.CUMULATIVE
                )
            ),
            Metric(
                attributes={"c": "d"},
                description="description",
                instrumentation_scope=self.mock_instrumentation_scope,
                name="name",
                resource=self.mock_resource,
                unit="unit",
                point=None,
            ),
        )
