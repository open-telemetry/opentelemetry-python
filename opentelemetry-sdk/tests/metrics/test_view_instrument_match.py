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

# pylint: disable=protected-access

from time import time_ns
from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

from opentelemetry.sdk.metrics._internal._view_instrument_match import (
    _ViewInstrumentMatch,
)
from opentelemetry.sdk.metrics._internal.aggregation import (
    _DropAggregation,
    _LastValueAggregation,
)
from opentelemetry.sdk.metrics._internal.instrument import _Counter
from opentelemetry.sdk.metrics._internal.measurement import Measurement
from opentelemetry.sdk.metrics._internal.sdk_configuration import (
    SdkConfiguration,
)
from opentelemetry.sdk.metrics.export import AggregationTemporality
from opentelemetry.sdk.metrics.view import (
    DefaultAggregation,
    DropAggregation,
    LastValueAggregation,
    View,
)


class Test_ViewInstrumentMatch(TestCase):  # pylint: disable=invalid-name
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
        instrument1 = _Counter(
            "instrument1",
            Mock(),
            Mock(),
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

        number_data_points = view_instrument_match.collect(
            AggregationTemporality.CUMULATIVE, 0
        )
        number_data_points = list(number_data_points)
        self.assertEqual(len(number_data_points), 1)

        number_data_point = number_data_points[0]

        self.assertEqual(number_data_point.attributes, {"c": "d"})
        self.assertEqual(number_data_point.value, 0)

    @patch(
        "opentelemetry.sdk.metrics._internal._view_instrument_match.time_ns",
        side_effect=[0, 1, 2],
    )
    def test_collect_resets_start_time_unix_nano(self, mock_time_ns):
        instrument = Mock(name="instrument")
        instrument.instrumentation_scope = self.mock_instrumentation_scope
        view_instrument_match = _ViewInstrumentMatch(
            view=View(
                instrument_name="instrument",
                name="name",
                aggregation=self.mock_aggregation_factory,
            ),
            instrument=instrument,
            instrument_class_aggregation=MagicMock(
                **{"__getitem__.return_value": DefaultAggregation()}
            ),
        )
        start_time_unix_nano = 0
        self.assertEqual(mock_time_ns.call_count, 0)

        # +1 call to _create_aggregation
        view_instrument_match.consume_measurement(
            Measurement(
                value=0, instrument=instrument, attributes={"foo": "bar0"}
            )
        )
        view_instrument_match._view._aggregation._create_aggregation.assert_called_with(
            instrument, {"foo": "bar0"}, start_time_unix_nano
        )
        collection_start_time_unix_nano = time_ns()
        collected_data_points = view_instrument_match.collect(
            AggregationTemporality.CUMULATIVE, collection_start_time_unix_nano
        )
        self.assertIsNotNone(collected_data_points)
        self.assertEqual(len(collected_data_points), 1)

        # +1 call to _create_aggregation
        view_instrument_match.consume_measurement(
            Measurement(
                value=0, instrument=instrument, attributes={"foo": "bar1"}
            )
        )
        view_instrument_match._view._aggregation._create_aggregation.assert_called_with(
            instrument, {"foo": "bar1"}, 1
        )
        collection_start_time_unix_nano = time_ns()
        collected_data_points = view_instrument_match.collect(
            AggregationTemporality.CUMULATIVE, collection_start_time_unix_nano
        )
        self.assertIsNotNone(collected_data_points)
        self.assertEqual(len(collected_data_points), 2)
        collected_data_points = view_instrument_match.collect(
            AggregationTemporality.CUMULATIVE, collection_start_time_unix_nano
        )
        # +1 call to create_aggregation
        view_instrument_match.consume_measurement(
            Measurement(
                value=0, instrument=instrument, attributes={"foo": "bar"}
            )
        )
        view_instrument_match._view._aggregation._create_aggregation.assert_called_with(
            instrument, {"foo": "bar"}, 2
        )
        # No new calls to _create_aggregation because attributes remain the same
        view_instrument_match.consume_measurement(
            Measurement(
                value=0, instrument=instrument, attributes={"foo": "bar"}
            )
        )
        view_instrument_match.consume_measurement(
            Measurement(
                value=0, instrument=instrument, attributes={"foo": "bar"}
            )
        )
        # In total we have 5 calls for _create_aggregation
        # 1 from the _ViewInstrumentMatch initialization and 4
        # from the consume_measurement calls with different attributes
        self.assertEqual(
            view_instrument_match._view._aggregation._create_aggregation.call_count,
            5,
        )

    def test_data_point_check(self):
        instrument1 = _Counter(
            "instrument1",
            Mock(),
            Mock(),
            description="description",
            unit="unit",
        )
        instrument1.instrumentation_scope = self.mock_instrumentation_scope

        view_instrument_match = _ViewInstrumentMatch(
            view=View(
                instrument_name="instrument1",
                name="name",
                aggregation=DefaultAggregation(),
            ),
            instrument=instrument1,
            instrument_class_aggregation=MagicMock(
                **{
                    "__getitem__.return_value": Mock(
                        **{
                            "_create_aggregation.return_value": Mock(
                                **{
                                    "collect.side_effect": [
                                        Mock(),
                                        Mock(),
                                        None,
                                        Mock(),
                                    ]
                                }
                            )
                        }
                    )
                }
            ),
        )

        view_instrument_match.consume_measurement(
            Measurement(
                value=0,
                instrument=Mock(name="instrument1"),
                attributes={"c": "d", "f": "g"},
            )
        )
        view_instrument_match.consume_measurement(
            Measurement(
                value=0,
                instrument=Mock(name="instrument1"),
                attributes={"h": "i", "j": "k"},
            )
        )
        view_instrument_match.consume_measurement(
            Measurement(
                value=0,
                instrument=Mock(name="instrument1"),
                attributes={"l": "m", "n": "o"},
            )
        )
        view_instrument_match.consume_measurement(
            Measurement(
                value=0,
                instrument=Mock(name="instrument1"),
                attributes={"p": "q", "r": "s"},
            )
        )

        result = view_instrument_match.collect(
            AggregationTemporality.CUMULATIVE, 0
        )

        self.assertEqual(len(list(result)), 3)

    def test_setting_aggregation(self):
        instrument1 = _Counter(
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
            instrument_class_aggregation={_Counter: LastValueAggregation()},
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
