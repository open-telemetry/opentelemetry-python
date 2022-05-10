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
from unittest.mock import MagicMock, Mock

from opentelemetry.sdk._metrics import Counter
from opentelemetry.sdk._metrics._internal._view_instrument_match import (
    _ViewInstrumentMatch,
)
from opentelemetry.sdk._metrics._internal.aggregation import (
    _DropAggregation,
    _LastValueAggregation,
)
from opentelemetry.sdk._metrics._internal.measurement import Measurement
from opentelemetry.sdk._metrics._internal.sdk_configuration import (
    SdkConfiguration,
)
from opentelemetry.sdk._metrics.export import AggregationTemporality, Metric
from opentelemetry.sdk._metrics.view import (
    DefaultAggregation,
    DropAggregation,
    LastValueAggregation,
    View,
)


class Test_ViewInstrumentMatch(TestCase):
    @classmethod
    def setUpClass(cls):

        cls.mock_aggregation_factory = Mock()
        cls.mock_created_aggregation = (
            cls.mock_aggregation_factory._create_aggregation()
        )
        cls.mock_resource = Mock()
        cls.mock_instrumentation_scope = Mock()
        cls.sdk_configuration = SdkConfiguration(
            resource=cls.mock_resource,
            metric_readers=[],
            views=[],
        )

    def test_consume_measurement(self):
        instrument1 = Mock(name="instrument1")
        instrument1.instrumentation_scope = self.mock_instrumentation_scope
        view_instrument_match = _ViewInstrumentMatch(
            view=View(
                instrument_name="instrument1",
                name="name",
                aggregation=self.mock_aggregation_factory,
                attribute_keys={"a", "c"},
            ),
            instrument=instrument1,
            sdk_config=self.sdk_configuration,
            instrument_class_temporality=MagicMock(
                **{
                    "__getitem__.return_value": AggregationTemporality.CUMULATIVE
                }
            ),
            instrument_class_aggregation=MagicMock(
                **{"__getitem__.return_value": DefaultAggregation()}
            ),
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
            sdk_config=self.sdk_configuration,
            instrument_class_temporality=MagicMock(
                **{
                    "__getitem__.return_value": AggregationTemporality.CUMULATIVE
                }
            ),
            instrument_class_aggregation=MagicMock(
                **{"__getitem__.return_value": DefaultAggregation()}
            ),
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

        # empty set attribute_keys will drop all labels and aggregate
        # everything together
        view_instrument_match = _ViewInstrumentMatch(
            view=View(
                instrument_name="instrument1",
                name="name",
                aggregation=self.mock_aggregation_factory,
                attribute_keys={},
            ),
            instrument=instrument1,
            sdk_config=self.sdk_configuration,
            instrument_class_temporality=MagicMock(
                **{
                    "__getitem__.return_value": AggregationTemporality.CUMULATIVE
                }
            ),
            instrument_class_aggregation=MagicMock(
                **{"__getitem__.return_value": DefaultAggregation()}
            ),
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
            sdk_config=self.sdk_configuration,
            instrument_class_temporality=MagicMock(
                **{
                    "__getitem__.return_value": AggregationTemporality.CUMULATIVE
                }
            ),
            instrument_class_aggregation=MagicMock(
                **{"__getitem__.return_value": DefaultAggregation()}
            ),
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
        view_instrument_match = _ViewInstrumentMatch(
            view=View(
                instrument_name="instrument1",
                name="name",
                aggregation=self.mock_aggregation_factory,
                attribute_keys={"a", "c"},
            ),
            instrument=instrument1,
            sdk_config=self.sdk_configuration,
            instrument_class_temporality=MagicMock(
                **{
                    "__getitem__.return_value": AggregationTemporality.CUMULATIVE
                }
            ),
            instrument_class_aggregation=MagicMock(
                **{"__getitem__.return_value": DefaultAggregation()}
            ),
        )

        view_instrument_match.consume_measurement(
            Measurement(
                value=0,
                instrument=Mock(name="instrument1"),
                attributes={"c": "d", "f": "g"},
            )
        )
        self.assertEqual(
            next(view_instrument_match.collect()),
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

    def test_setting_aggregation(self):
        instrument1 = Counter(
            name="instrument1",
            instrumentation_scope=Mock(),
            measurement_consumer=Mock(),
            description="description",
            unit="unit",
        )
        instrument1.instrumentation_scope = self.mock_instrumentation_scope
        view_instrument_match = _ViewInstrumentMatch(
            view=View(
                instrument_name="instrument1",
                name="name",
                aggregation=DefaultAggregation(),
                attribute_keys={"a", "c"},
            ),
            instrument=instrument1,
            sdk_config=self.sdk_configuration,
            instrument_class_temporality=MagicMock(
                **{
                    "__getitem__.return_value": AggregationTemporality.CUMULATIVE
                }
            ),
            instrument_class_aggregation={Counter: LastValueAggregation()},
        )

        view_instrument_match.consume_measurement(
            Measurement(
                value=0,
                instrument=Mock(name="instrument1"),
                attributes={"c": "d", "f": "g"},
            )
        )

        self.assertIsInstance(
            view_instrument_match._attributes_aggregation[
                frozenset({("c", "d")})
            ],
            _LastValueAggregation,
        )
