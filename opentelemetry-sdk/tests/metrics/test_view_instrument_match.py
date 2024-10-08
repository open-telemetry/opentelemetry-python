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
from typing import Callable, Sequence, Type
from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

from opentelemetry.context import Context
from opentelemetry.sdk.metrics._internal._view_instrument_match import (
    _ViewInstrumentMatch,
)
from opentelemetry.sdk.metrics._internal.aggregation import (
    _Aggregation,
    _DropAggregation,
    _ExplicitBucketHistogramAggregation,
    _LastValueAggregation,
)
from opentelemetry.sdk.metrics._internal.exemplar import (
    AlignedHistogramBucketExemplarReservoir,
    ExemplarReservoirBuilder,
    SimpleFixedSizeExemplarReservoir,
)
from opentelemetry.sdk.metrics._internal.instrument import _Counter, _Histogram
from opentelemetry.sdk.metrics._internal.measurement import Measurement
from opentelemetry.sdk.metrics._internal.sdk_configuration import (
    SdkConfiguration,
)
from opentelemetry.sdk.metrics._internal.view import _default_reservoir_factory
from opentelemetry.sdk.metrics.export import AggregationTemporality
from opentelemetry.sdk.metrics.view import (
    DefaultAggregation,
    DropAggregation,
    LastValueAggregation,
    View,
)


def generalized_reservoir_factory(
    size: int = 1, boundaries: Sequence[float] = None
) -> Callable[[Type[_Aggregation]], ExemplarReservoirBuilder]:
    def factory(
        aggregation_type: Type[_Aggregation],
    ) -> ExemplarReservoirBuilder:
        if issubclass(aggregation_type, _ExplicitBucketHistogramAggregation):
            return lambda **kwargs: AlignedHistogramBucketExemplarReservoir(
                boundaries=boundaries or [],
                **{k: v for k, v in kwargs.items() if k != "boundaries"},
            )

        return lambda **kwargs: SimpleFixedSizeExemplarReservoir(
            size=size,
            **{k: v for k, v in kwargs.items() if k != "size"},
        )

    return factory


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
            exemplar_filter=Mock(),
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
                time_unix_nano=time_ns(),
                instrument=instrument1,
                context=Context(),
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
                time_unix_nano=time_ns(),
                instrument=instrument1,
                context=Context(),
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
                time_unix_nano=time_ns(),
                instrument=instrument1,
                context=Context(),
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
            Measurement(
                value=0,
                time_unix_nano=time_ns(),
                instrument=instrument1,
                context=Context(),
                attributes=None,
            )
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
            Measurement(
                value=0,
                time_unix_nano=time_ns(),
                instrument=instrument1,
                context=Context(),
                attributes=None,
            )
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
                time_unix_nano=time_ns(),
                instrument=Mock(name="instrument1"),
                context=Context(),
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
                value=0,
                time_unix_nano=time_ns(),
                instrument=instrument,
                attributes={"foo": "bar0"},
                context=Context(),
            )
        )
        view_instrument_match._view._aggregation._create_aggregation.assert_called_with(
            instrument,
            {"foo": "bar0"},
            _default_reservoir_factory,
            start_time_unix_nano,
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
                value=0,
                time_unix_nano=time_ns(),
                instrument=instrument,
                attributes={"foo": "bar1"},
                context=Context(),
            )
        )
        view_instrument_match._view._aggregation._create_aggregation.assert_called_with(
            instrument, {"foo": "bar1"}, _default_reservoir_factory, 1
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
                value=0,
                time_unix_nano=time_ns(),
                instrument=instrument,
                attributes={"foo": "bar"},
                context=Context(),
            )
        )
        view_instrument_match._view._aggregation._create_aggregation.assert_called_with(
            instrument, {"foo": "bar"}, _default_reservoir_factory, 2
        )
        # No new calls to _create_aggregation because attributes remain the same
        view_instrument_match.consume_measurement(
            Measurement(
                value=0,
                time_unix_nano=time_ns(),
                instrument=instrument,
                attributes={"foo": "bar"},
                context=Context(),
            )
        )
        view_instrument_match.consume_measurement(
            Measurement(
                value=0,
                time_unix_nano=time_ns(),
                instrument=instrument,
                attributes={"foo": "bar"},
                context=Context(),
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
                time_unix_nano=time_ns(),
                instrument=Mock(name="instrument1"),
                context=Context(),
                attributes={"c": "d", "f": "g"},
            )
        )
        view_instrument_match.consume_measurement(
            Measurement(
                value=0,
                time_unix_nano=time_ns(),
                instrument=Mock(name="instrument1"),
                context=Context(),
                attributes={"h": "i", "j": "k"},
            )
        )
        view_instrument_match.consume_measurement(
            Measurement(
                value=0,
                time_unix_nano=time_ns(),
                instrument=Mock(name="instrument1"),
                context=Context(),
                attributes={"l": "m", "n": "o"},
            )
        )
        view_instrument_match.consume_measurement(
            Measurement(
                value=0,
                time_unix_nano=time_ns(),
                instrument=Mock(name="instrument1"),
                context=Context(),
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
                time_unix_nano=time_ns(),
                instrument=Mock(name="instrument1"),
                context=Context(),
                attributes={"c": "d", "f": "g"},
            )
        )

        self.assertIsInstance(
            view_instrument_match._attributes_aggregation[
                frozenset({("c", "d")})
            ],
            _LastValueAggregation,
        )


class TestSimpleFixedSizeExemplarReservoir(TestCase):
    def test_consume_measurement_with_custom_reservoir_factory(self):
        simple_fixed_size_factory = generalized_reservoir_factory(size=10)

        # Create an instance of _Counter
        instrument1 = _Counter(
            name="instrument1",
            instrumentation_scope=None,
            measurement_consumer=None,
            description="description",
            unit="unit",
        )

        view_instrument_match = _ViewInstrumentMatch(
            view=View(
                instrument_name="instrument1",
                name="name",
                aggregation=DefaultAggregation(),
                exemplar_reservoir_factory=simple_fixed_size_factory,
            ),
            instrument=instrument1,
            instrument_class_aggregation={_Counter: DefaultAggregation()},
        )

        # Consume measurements with the same attributes to ensure aggregation
        view_instrument_match.consume_measurement(
            Measurement(
                value=2.0,
                time_unix_nano=time_ns(),
                instrument=instrument1,
                context=Context(),
                attributes={"attribute1": "value1"},
            )
        )

        view_instrument_match.consume_measurement(
            Measurement(
                value=4.0,
                time_unix_nano=time_ns(),
                instrument=instrument1,
                context=Context(),
                attributes={"attribute2": "value2"},
            )
        )

        view_instrument_match.consume_measurement(
            Measurement(
                value=5.0,
                time_unix_nano=time_ns(),
                instrument=instrument1,
                context=Context(),
                attributes={"attribute2": "value2"},
            )
        )

        data_points = list(
            view_instrument_match.collect(AggregationTemporality.CUMULATIVE, 0)
        )

        # Ensure only one data point is collected
        self.assertEqual(len(data_points), 2)

        # Verify that exemplars have been correctly stored and collected
        self.assertEqual(len(data_points[0].exemplars), 1)
        self.assertEqual(len(data_points[1].exemplars), 2)

        self.assertEqual(data_points[0].exemplars[0].value, 2.0)
        self.assertEqual(data_points[1].exemplars[0].value, 4.0)
        self.assertEqual(data_points[1].exemplars[1].value, 5.0)

    def test_consume_measurement_with_exemplars(self):
        # Create an instance of _Counter
        instrument1 = _Counter(
            name="instrument1",
            instrumentation_scope=None,  # No mock, set to None or actual scope if available
            measurement_consumer=None,  # No mock, set to None or actual consumer if available
            description="description",
            unit="unit",
        )

        view_instrument_match = _ViewInstrumentMatch(
            view=View(
                instrument_name="instrument1",
                name="name",
                aggregation=DefaultAggregation(),
            ),
            instrument=instrument1,
            instrument_class_aggregation={_Counter: DefaultAggregation()},
        )

        # Consume measurements with the same attributes to ensure aggregation
        view_instrument_match.consume_measurement(
            Measurement(
                value=4.0,
                time_unix_nano=time_ns(),
                instrument=instrument1,
                context=Context(),
                attributes={"attribute2": "value2"},
            )
        )

        view_instrument_match.consume_measurement(
            Measurement(
                value=5.0,
                time_unix_nano=time_ns(),
                instrument=instrument1,
                context=Context(),
                attributes={"attribute2": "value2"},
            )
        )

        # Collect the data points
        data_points = list(
            view_instrument_match.collect(AggregationTemporality.CUMULATIVE, 0)
        )

        # Ensure only one data point is collected
        self.assertEqual(len(data_points), 1)

        # Verify that exemplars have been correctly stored and collected
        # As the default reservoir as only one bucket, it will retain
        # either one of the measurements based on random selection
        self.assertEqual(len(data_points[0].exemplars), 1)

        self.assertIn(data_points[0].exemplars[0].value, [4.0, 5.0])

    def test_consume_measurement_with_exemplars_and_view_attributes_filter(
        self,
    ):
        value = 22
        # Create an instance of _Counter
        instrument1 = _Counter(
            name="instrument1",
            instrumentation_scope=None,  # No mock, set to None or actual scope if available
            measurement_consumer=None,  # No mock, set to None or actual consumer if available
        )

        view_instrument_match = _ViewInstrumentMatch(
            view=View(
                instrument_name="instrument1",
                name="name",
                attribute_keys={"X", "Y"},
            ),
            instrument=instrument1,
            instrument_class_aggregation={_Counter: DefaultAggregation()},
        )

        view_instrument_match.consume_measurement(
            Measurement(
                value=value,
                time_unix_nano=time_ns(),
                instrument=instrument1,
                context=Context(),
                attributes={"X": "x-value", "Y": "y-value", "Z": "z-value"},
            )
        )

        # Collect the data points
        data_points = list(
            view_instrument_match.collect(AggregationTemporality.CUMULATIVE, 0)
        )

        # Ensure only one data point is collected
        self.assertEqual(len(data_points), 1)

        # Verify that exemplars have been correctly stored and collected
        self.assertEqual(len(data_points[0].exemplars), 1)

        # Check the exemplar has the dropped attribute
        exemplar = list(data_points[0].exemplars)[0]
        self.assertEqual(exemplar.value, value)
        self.assertDictEqual(exemplar.filtered_attributes, {"Z": "z-value"})


class TestAlignedHistogramBucketExemplarReservoir(TestCase):
    def test_consume_measurement_with_custom_reservoir_factory(self):
        # Custom factory for AlignedHistogramBucketExemplarReservoir with specific boundaries
        histogram_reservoir_factory = generalized_reservoir_factory(
            boundaries=[0, 5, 10, 25]
        )

        # Create an instance of _Histogram
        instrument1 = _Histogram(
            name="instrument1",
            instrumentation_scope=None,
            measurement_consumer=None,
            description="description",
            unit="unit",
        )

        view_instrument_match = _ViewInstrumentMatch(
            view=View(
                instrument_name="instrument1",
                name="name",
                aggregation=DefaultAggregation(),
                exemplar_reservoir_factory=histogram_reservoir_factory,
            ),
            instrument=instrument1,
            instrument_class_aggregation={_Histogram: DefaultAggregation()},
        )

        # Consume measurements with different values to ensure they are placed in the correct buckets
        view_instrument_match.consume_measurement(
            Measurement(
                value=2.0,  # Should go into the first bucket (0 to 5)
                time_unix_nano=time_ns(),
                instrument=instrument1,
                context=Context(),
                attributes={"attribute1": "value1"},
            )
        )

        view_instrument_match.consume_measurement(
            Measurement(
                value=7.0,  # Should go into the second bucket (5 to 10)
                time_unix_nano=time_ns(),
                instrument=instrument1,
                context=Context(),
                attributes={"attribute2": "value2"},
            )
        )

        view_instrument_match.consume_measurement(
            Measurement(
                value=8.0,  # Should go into the second bucket (5 to 10)
                time_unix_nano=time_ns(),
                instrument=instrument1,
                context=Context(),
                attributes={"attribute2": "value2"},
            )
        )

        view_instrument_match.consume_measurement(
            Measurement(
                value=15.0,  # Should go into the third bucket (10 to 25)
                time_unix_nano=time_ns(),
                instrument=instrument1,
                context=Context(),
                attributes={"attribute3": "value3"},
            )
        )

        # Collect the data points
        data_points = list(
            view_instrument_match.collect(AggregationTemporality.CUMULATIVE, 0)
        )

        # Ensure three data points are collected, one for each bucket
        self.assertEqual(len(data_points), 3)

        # Verify that exemplars have been correctly stored and collected in their respective buckets
        self.assertEqual(len(data_points[0].exemplars), 1)
        self.assertEqual(len(data_points[1].exemplars), 1)
        self.assertEqual(len(data_points[2].exemplars), 1)

        self.assertEqual(
            data_points[0].exemplars[0].value, 2.0
        )  # First bucket
        self.assertEqual(
            data_points[1].exemplars[0].value, 8.0
        )  # Second bucket
        self.assertEqual(
            data_points[2].exemplars[0].value, 15.0
        )  # Third bucket
