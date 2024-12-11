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

# pylint: disable=protected-access,invalid-name

from logging import WARNING
from time import time_ns
from unittest.mock import MagicMock, Mock, patch

from opentelemetry.context import Context
from opentelemetry.sdk.metrics._internal.aggregation import (
    _LastValueAggregation,
)
from opentelemetry.sdk.metrics._internal.instrument import (
    _Counter,
    _Gauge,
    _Histogram,
    _ObservableCounter,
    _UpDownCounter,
)
from opentelemetry.sdk.metrics._internal.measurement import Measurement
from opentelemetry.sdk.metrics._internal.metric_reader_storage import (
    _DEFAULT_VIEW,
    MetricReaderStorage,
)
from opentelemetry.sdk.metrics._internal.sdk_configuration import (
    SdkConfiguration,
)
from opentelemetry.sdk.metrics.export import AggregationTemporality
from opentelemetry.sdk.metrics.view import (
    DefaultAggregation,
    DropAggregation,
    ExplicitBucketHistogramAggregation,
    SumAggregation,
    View,
)
from opentelemetry.test.concurrency_test import ConcurrencyTestBase, MockFunc


def mock_view_matching(name, *instruments) -> Mock:
    mock = Mock(name=name)
    mock._match.side_effect = lambda instrument: instrument in instruments
    return mock


def mock_instrument() -> Mock:
    instr = Mock()
    instr.attributes = {}
    return instr


class TestMetricReaderStorage(ConcurrencyTestBase):
    @patch(
        "opentelemetry.sdk.metrics._internal"
        ".metric_reader_storage._ViewInstrumentMatch"
    )
    def test_creates_view_instrument_matches(
        self, MockViewInstrumentMatch: Mock
    ):
        """It should create a MockViewInstrumentMatch when an instrument
        matches a view"""
        instrument1 = Mock(name="instrument1")
        instrument2 = Mock(name="instrument2")

        view1 = mock_view_matching("view_1", instrument1)
        view2 = mock_view_matching("view_2", instrument1, instrument2)
        storage = MetricReaderStorage(
            SdkConfiguration(
                exemplar_filter=Mock(),
                resource=Mock(),
                metric_readers=(),
                views=(view1, view2),
            ),
            MagicMock(
                **{
                    "__getitem__.return_value": AggregationTemporality.CUMULATIVE
                }
            ),
            MagicMock(**{"__getitem__.return_value": DefaultAggregation()}),
        )

        # instrument1 matches view1 and view2, so should create two
        # ViewInstrumentMatch objects
        storage.consume_measurement(
            Measurement(1, time_ns(), instrument1, Context())
        )
        self.assertEqual(
            len(MockViewInstrumentMatch.call_args_list),
            2,
            MockViewInstrumentMatch.mock_calls,
        )
        # they should only be created the first time the instrument is seen
        storage.consume_measurement(
            Measurement(1, time_ns(), instrument1, Context())
        )
        self.assertEqual(len(MockViewInstrumentMatch.call_args_list), 2)

        # instrument2 matches view2, so should create a single
        # ViewInstrumentMatch
        MockViewInstrumentMatch.call_args_list.clear()
        with self.assertLogs(level=WARNING):
            storage.consume_measurement(
                Measurement(1, time_ns(), instrument2, Context())
            )
        self.assertEqual(len(MockViewInstrumentMatch.call_args_list), 1)

    @patch(
        "opentelemetry.sdk.metrics._internal."
        "metric_reader_storage._ViewInstrumentMatch"
    )
    def test_forwards_calls_to_view_instrument_match(
        self, MockViewInstrumentMatch: Mock
    ):
        view_instrument_match1 = Mock(
            _aggregation=_LastValueAggregation({}, Mock())
        )
        view_instrument_match2 = Mock(
            _aggregation=_LastValueAggregation({}, Mock())
        )
        view_instrument_match3 = Mock(
            _aggregation=_LastValueAggregation({}, Mock())
        )
        MockViewInstrumentMatch.side_effect = [
            view_instrument_match1,
            view_instrument_match2,
            view_instrument_match3,
        ]

        instrument1 = Mock(name="instrument1")
        instrument2 = Mock(name="instrument2")
        view1 = mock_view_matching("view1", instrument1)
        view2 = mock_view_matching("view2", instrument1, instrument2)

        storage = MetricReaderStorage(
            SdkConfiguration(
                exemplar_filter=Mock(),
                resource=Mock(),
                metric_readers=(),
                views=(view1, view2),
            ),
            MagicMock(
                **{
                    "__getitem__.return_value": AggregationTemporality.CUMULATIVE
                }
            ),
            MagicMock(**{"__getitem__.return_value": DefaultAggregation()}),
        )

        # Measurements from an instrument should be passed on to each
        # ViewInstrumentMatch objects created for that instrument
        measurement = Measurement(1, time_ns(), instrument1, Context())
        storage.consume_measurement(measurement)
        view_instrument_match1.consume_measurement.assert_called_once_with(
            measurement, True
        )
        view_instrument_match2.consume_measurement.assert_called_once_with(
            measurement, True
        )
        view_instrument_match3.consume_measurement.assert_not_called()

        measurement = Measurement(1, time_ns(), instrument2, Context())
        with self.assertLogs(level=WARNING):
            storage.consume_measurement(measurement)
        view_instrument_match3.consume_measurement.assert_called_once_with(
            measurement, True
        )

        # collect() should call collect on all of its _ViewInstrumentMatch
        # objects and combine them together
        all_metrics = [Mock() for _ in range(6)]
        view_instrument_match1.collect.return_value = all_metrics[:2]
        view_instrument_match2.collect.return_value = all_metrics[2:4]
        view_instrument_match3.collect.return_value = all_metrics[4:]

        result = storage.collect()
        view_instrument_match1.collect.assert_called_once()
        view_instrument_match2.collect.assert_called_once()
        view_instrument_match3.collect.assert_called_once()
        self.assertEqual(
            (
                result.resource_metrics[0]
                .scope_metrics[0]
                .metrics[0]
                .data.data_points[0]
            ),
            all_metrics[0],
        )
        self.assertEqual(
            (
                result.resource_metrics[0]
                .scope_metrics[0]
                .metrics[0]
                .data.data_points[1]
            ),
            all_metrics[1],
        )
        self.assertEqual(
            (
                result.resource_metrics[0]
                .scope_metrics[0]
                .metrics[1]
                .data.data_points[0]
            ),
            all_metrics[2],
        )
        self.assertEqual(
            (
                result.resource_metrics[0]
                .scope_metrics[0]
                .metrics[1]
                .data.data_points[1]
            ),
            all_metrics[3],
        )
        self.assertEqual(
            (
                result.resource_metrics[0]
                .scope_metrics[1]
                .metrics[0]
                .data.data_points[0]
            ),
            all_metrics[4],
        )
        self.assertEqual(
            (
                result.resource_metrics[0]
                .scope_metrics[1]
                .metrics[0]
                .data.data_points[1]
            ),
            all_metrics[5],
        )

    @patch(
        "opentelemetry.sdk.metrics._internal."
        "metric_reader_storage._ViewInstrumentMatch"
    )
    def test_race_concurrent_measurements(self, MockViewInstrumentMatch: Mock):
        mock_view_instrument_match_ctor = MockFunc()
        MockViewInstrumentMatch.side_effect = mock_view_instrument_match_ctor

        instrument1 = Mock(name="instrument1")
        view1 = mock_view_matching(instrument1)
        storage = MetricReaderStorage(
            SdkConfiguration(
                exemplar_filter=Mock(),
                resource=Mock(),
                metric_readers=(),
                views=(view1,),
            ),
            MagicMock(
                **{
                    "__getitem__.return_value": AggregationTemporality.CUMULATIVE
                }
            ),
            MagicMock(**{"__getitem__.return_value": DefaultAggregation()}),
        )

        def send_measurement():
            storage.consume_measurement(
                Measurement(1, time_ns(), instrument1, Context())
            )

        # race sending many measurements concurrently
        self.run_with_many_threads(send_measurement)

        # _ViewInstrumentMatch constructor should have only been called once
        self.assertEqual(mock_view_instrument_match_ctor.call_count, 1)

    @patch(
        "opentelemetry.sdk.metrics._internal."
        "metric_reader_storage._ViewInstrumentMatch"
    )
    def test_default_view_enabled(self, MockViewInstrumentMatch: Mock):
        """Instruments should be matched with default views when enabled"""
        instrument1 = Mock(name="instrument1")
        instrument2 = Mock(name="instrument2")

        storage = MetricReaderStorage(
            SdkConfiguration(
                exemplar_filter=Mock(),
                resource=Mock(),
                metric_readers=(),
                views=(),
            ),
            MagicMock(
                **{
                    "__getitem__.return_value": AggregationTemporality.CUMULATIVE
                }
            ),
            MagicMock(**{"__getitem__.return_value": DefaultAggregation()}),
        )

        storage.consume_measurement(
            Measurement(1, time_ns(), instrument1, Context())
        )
        self.assertEqual(
            len(MockViewInstrumentMatch.call_args_list),
            1,
            MockViewInstrumentMatch.mock_calls,
        )
        storage.consume_measurement(
            Measurement(1, time_ns(), instrument1, Context())
        )
        self.assertEqual(len(MockViewInstrumentMatch.call_args_list), 1)

        MockViewInstrumentMatch.call_args_list.clear()
        storage.consume_measurement(
            Measurement(1, time_ns(), instrument2, Context())
        )
        self.assertEqual(len(MockViewInstrumentMatch.call_args_list), 1)

    def test_drop_aggregation(self):
        counter = _Counter("name", Mock(), Mock())
        metric_reader_storage = MetricReaderStorage(
            SdkConfiguration(
                exemplar_filter=Mock(),
                resource=Mock(),
                metric_readers=(),
                views=(
                    View(
                        instrument_name="name", aggregation=DropAggregation()
                    ),
                ),
            ),
            MagicMock(
                **{
                    "__getitem__.return_value": AggregationTemporality.CUMULATIVE
                }
            ),
            MagicMock(**{"__getitem__.return_value": DefaultAggregation()}),
        )
        metric_reader_storage.consume_measurement(
            Measurement(1, time_ns(), counter, Context())
        )

        self.assertIsNone(metric_reader_storage.collect())

    def test_same_collection_start(self):
        counter = _Counter("name", Mock(), Mock())
        up_down_counter = _UpDownCounter("name", Mock(), Mock())

        metric_reader_storage = MetricReaderStorage(
            SdkConfiguration(
                exemplar_filter=Mock(),
                resource=Mock(),
                metric_readers=(),
                views=(View(instrument_name="name"),),
            ),
            MagicMock(
                **{
                    "__getitem__.return_value": AggregationTemporality.CUMULATIVE
                }
            ),
            MagicMock(**{"__getitem__.return_value": DefaultAggregation()}),
        )

        metric_reader_storage.consume_measurement(
            Measurement(1, time_ns(), counter, Context())
        )
        metric_reader_storage.consume_measurement(
            Measurement(1, time_ns(), up_down_counter, Context())
        )

        actual = metric_reader_storage.collect()

        self.assertEqual(
            list(
                actual.resource_metrics[0]
                .scope_metrics[0]
                .metrics[0]
                .data.data_points
            )[0].time_unix_nano,
            list(
                actual.resource_metrics[0]
                .scope_metrics[1]
                .metrics[0]
                .data.data_points
            )[0].time_unix_nano,
        )

    def test_conflicting_view_configuration(self):
        observable_counter = _ObservableCounter(
            "observable_counter",
            Mock(),
            [Mock()],
            unit="unit",
            description="description",
        )
        metric_reader_storage = MetricReaderStorage(
            SdkConfiguration(
                exemplar_filter=Mock(),
                resource=Mock(),
                metric_readers=(),
                views=(
                    View(
                        instrument_name="observable_counter",
                        aggregation=ExplicitBucketHistogramAggregation(),
                    ),
                ),
            ),
            MagicMock(
                **{
                    "__getitem__.return_value": AggregationTemporality.CUMULATIVE
                }
            ),
            MagicMock(**{"__getitem__.return_value": DefaultAggregation()}),
        )

        with self.assertLogs(level=WARNING):
            metric_reader_storage.consume_measurement(
                Measurement(1, time_ns(), observable_counter, Context())
            )

        self.assertIs(
            metric_reader_storage._instrument_view_instrument_matches[
                observable_counter
            ][0]._view,
            _DEFAULT_VIEW,
        )

    def test_view_instrument_match_conflict_0(self):
        # There is a conflict between views and instruments.

        observable_counter_0 = _ObservableCounter(
            "observable_counter_0",
            Mock(),
            [Mock()],
            unit="unit",
            description="description",
        )
        observable_counter_1 = _ObservableCounter(
            "observable_counter_1",
            Mock(),
            [Mock()],
            unit="unit",
            description="description",
        )
        metric_reader_storage = MetricReaderStorage(
            SdkConfiguration(
                exemplar_filter=Mock(),
                resource=Mock(),
                metric_readers=(),
                views=(
                    View(instrument_name="observable_counter_0", name="foo"),
                    View(instrument_name="observable_counter_1", name="foo"),
                ),
            ),
            MagicMock(
                **{
                    "__getitem__.return_value": AggregationTemporality.CUMULATIVE
                }
            ),
            MagicMock(**{"__getitem__.return_value": DefaultAggregation()}),
        )

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=WARNING):
                metric_reader_storage.consume_measurement(
                    Measurement(1, time_ns(), observable_counter_0, Context())
                )

        with self.assertLogs(level=WARNING) as log:
            metric_reader_storage.consume_measurement(
                Measurement(1, time_ns(), observable_counter_1, Context())
            )

        self.assertIn(
            "will cause conflicting metrics",
            log.records[0].message,
        )

    def test_view_instrument_match_conflict_1(self):
        # There is a conflict between views and instruments.

        observable_counter_foo = _ObservableCounter(
            "foo",
            Mock(),
            [Mock()],
            unit="unit",
            description="description",
        )
        observable_counter_bar = _ObservableCounter(
            "bar",
            Mock(),
            [Mock()],
            unit="unit",
            description="description",
        )
        observable_counter_baz = _ObservableCounter(
            "baz",
            Mock(),
            [Mock()],
            unit="unit",
            description="description",
        )
        metric_reader_storage = MetricReaderStorage(
            SdkConfiguration(
                exemplar_filter=Mock(),
                resource=Mock(),
                metric_readers=(),
                views=(
                    View(instrument_name="bar", name="foo"),
                    View(instrument_name="baz", name="foo"),
                ),
            ),
            MagicMock(
                **{
                    "__getitem__.return_value": AggregationTemporality.CUMULATIVE
                }
            ),
            MagicMock(**{"__getitem__.return_value": DefaultAggregation()}),
        )

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=WARNING):
                metric_reader_storage.consume_measurement(
                    Measurement(
                        1, time_ns(), observable_counter_foo, Context()
                    )
                )

        with self.assertLogs(level=WARNING) as log:
            metric_reader_storage.consume_measurement(
                Measurement(1, time_ns(), observable_counter_bar, Context())
            )

        self.assertIn(
            "will cause conflicting metrics",
            log.records[0].message,
        )

        with self.assertLogs(level=WARNING) as log:
            metric_reader_storage.consume_measurement(
                Measurement(1, time_ns(), observable_counter_baz, Context())
            )

        self.assertIn(
            "will cause conflicting metrics",
            log.records[0].message,
        )

        for view_instrument_matches in (
            metric_reader_storage._instrument_view_instrument_matches.values()
        ):
            for view_instrument_match in view_instrument_matches:
                self.assertEqual(view_instrument_match._name, "foo")

    def test_view_instrument_match_conflict_2(self):
        # There is no conflict because the metric streams names are different.
        observable_counter_foo = _ObservableCounter(
            "foo",
            Mock(),
            [Mock()],
            unit="unit",
            description="description",
        )
        observable_counter_bar = _ObservableCounter(
            "bar",
            Mock(),
            [Mock()],
            unit="unit",
            description="description",
        )

        metric_reader_storage = MetricReaderStorage(
            SdkConfiguration(
                exemplar_filter=Mock(),
                resource=Mock(),
                metric_readers=(),
                views=(
                    View(instrument_name="foo"),
                    View(instrument_name="bar"),
                ),
            ),
            MagicMock(
                **{
                    "__getitem__.return_value": AggregationTemporality.CUMULATIVE
                }
            ),
            MagicMock(**{"__getitem__.return_value": DefaultAggregation()}),
        )

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=WARNING):
                metric_reader_storage.consume_measurement(
                    Measurement(
                        1, time_ns(), observable_counter_foo, Context()
                    )
                )

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=WARNING):
                metric_reader_storage.consume_measurement(
                    Measurement(
                        1, time_ns(), observable_counter_bar, Context()
                    )
                )

    def test_view_instrument_match_conflict_3(self):
        # There is no conflict because the aggregation temporality of the
        # instruments is different.

        counter_bar = _Counter(
            "bar",
            Mock(),
            [Mock()],
            unit="unit",
            description="description",
        )
        observable_counter_baz = _ObservableCounter(
            "baz",
            Mock(),
            [Mock()],
            unit="unit",
            description="description",
        )

        metric_reader_storage = MetricReaderStorage(
            SdkConfiguration(
                exemplar_filter=Mock(),
                resource=Mock(),
                metric_readers=(),
                views=(
                    View(instrument_name="bar", name="foo"),
                    View(instrument_name="baz", name="foo"),
                ),
            ),
            MagicMock(
                **{
                    "__getitem__.return_value": AggregationTemporality.CUMULATIVE
                }
            ),
            MagicMock(**{"__getitem__.return_value": DefaultAggregation()}),
        )

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=WARNING):
                metric_reader_storage.consume_measurement(
                    Measurement(1, time_ns(), counter_bar, Context())
                )

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=WARNING):
                metric_reader_storage.consume_measurement(
                    Measurement(
                        1, time_ns(), observable_counter_baz, Context()
                    )
                )

    def test_view_instrument_match_conflict_4(self):
        # There is no conflict because the monotonicity of the instruments is
        # different.

        counter_bar = _Counter(
            "bar",
            Mock(),
            [Mock()],
            unit="unit",
            description="description",
        )
        up_down_counter_baz = _UpDownCounter(
            "baz",
            Mock(),
            [Mock()],
            unit="unit",
            description="description",
        )

        metric_reader_storage = MetricReaderStorage(
            SdkConfiguration(
                exemplar_filter=Mock(),
                resource=Mock(),
                metric_readers=(),
                views=(
                    View(instrument_name="bar", name="foo"),
                    View(instrument_name="baz", name="foo"),
                ),
            ),
            MagicMock(
                **{
                    "__getitem__.return_value": AggregationTemporality.CUMULATIVE
                }
            ),
            MagicMock(**{"__getitem__.return_value": DefaultAggregation()}),
        )

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=WARNING):
                metric_reader_storage.consume_measurement(
                    Measurement(1, time_ns(), counter_bar, Context())
                )

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=WARNING):
                metric_reader_storage.consume_measurement(
                    Measurement(1, time_ns(), up_down_counter_baz, Context())
                )

    def test_view_instrument_match_conflict_5(self):
        # There is no conflict because the instrument units are different.

        observable_counter_0 = _ObservableCounter(
            "observable_counter_0",
            Mock(),
            [Mock()],
            unit="unit_0",
            description="description",
        )
        observable_counter_1 = _ObservableCounter(
            "observable_counter_1",
            Mock(),
            [Mock()],
            unit="unit_1",
            description="description",
        )
        metric_reader_storage = MetricReaderStorage(
            SdkConfiguration(
                exemplar_filter=Mock(),
                resource=Mock(),
                metric_readers=(),
                views=(
                    View(instrument_name="observable_counter_0", name="foo"),
                    View(instrument_name="observable_counter_1", name="foo"),
                ),
            ),
            MagicMock(
                **{
                    "__getitem__.return_value": AggregationTemporality.CUMULATIVE
                }
            ),
            MagicMock(**{"__getitem__.return_value": DefaultAggregation()}),
        )

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=WARNING):
                metric_reader_storage.consume_measurement(
                    Measurement(1, time_ns(), observable_counter_0, Context())
                )

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=WARNING):
                metric_reader_storage.consume_measurement(
                    Measurement(1, time_ns(), observable_counter_1, Context())
                )

    def test_view_instrument_match_conflict_6(self):
        # There is no conflict because the instrument data points are
        # different.

        observable_counter = _ObservableCounter(
            "observable_counter",
            Mock(),
            [Mock()],
            unit="unit",
            description="description",
        )
        histogram = _Histogram(
            "histogram",
            Mock(),
            [Mock()],
            unit="unit",
            description="description",
        )
        gauge = _Gauge(
            "gauge",
            Mock(),
            [Mock()],
            unit="unit",
            description="description",
        )
        metric_reader_storage = MetricReaderStorage(
            SdkConfiguration(
                exemplar_filter=Mock(),
                resource=Mock(),
                metric_readers=(),
                views=(
                    View(instrument_name="observable_counter", name="foo"),
                    View(instrument_name="histogram", name="foo"),
                    View(instrument_name="gauge", name="foo"),
                ),
            ),
            MagicMock(
                **{
                    "__getitem__.return_value": AggregationTemporality.CUMULATIVE
                }
            ),
            MagicMock(**{"__getitem__.return_value": DefaultAggregation()}),
        )

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=WARNING):
                metric_reader_storage.consume_measurement(
                    Measurement(1, time_ns(), observable_counter, Context())
                )

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=WARNING):
                metric_reader_storage.consume_measurement(
                    Measurement(1, time_ns(), histogram, Context())
                )

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=WARNING):
                metric_reader_storage.consume_measurement(
                    Measurement(1, time_ns(), gauge, Context())
                )

    def test_view_instrument_match_conflict_7(self):
        # There is a conflict between views and instruments because the
        # description being different does not avoid a conflict.

        observable_counter_0 = _ObservableCounter(
            "observable_counter_0",
            Mock(),
            [Mock()],
            unit="unit",
            description="description_0",
        )
        observable_counter_1 = _ObservableCounter(
            "observable_counter_1",
            Mock(),
            [Mock()],
            unit="unit",
            description="description_1",
        )
        metric_reader_storage = MetricReaderStorage(
            SdkConfiguration(
                exemplar_filter=Mock(),
                resource=Mock(),
                metric_readers=(),
                views=(
                    View(instrument_name="observable_counter_0", name="foo"),
                    View(instrument_name="observable_counter_1", name="foo"),
                ),
            ),
            MagicMock(
                **{
                    "__getitem__.return_value": AggregationTemporality.CUMULATIVE
                }
            ),
            MagicMock(**{"__getitem__.return_value": DefaultAggregation()}),
        )

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=WARNING):
                metric_reader_storage.consume_measurement(
                    Measurement(1, time_ns(), observable_counter_0, Context())
                )

        with self.assertLogs(level=WARNING) as log:
            metric_reader_storage.consume_measurement(
                Measurement(1, time_ns(), observable_counter_1, Context())
            )

        self.assertIn(
            "will cause conflicting metrics",
            log.records[0].message,
        )

    def test_view_instrument_match_conflict_8(self):
        # There is a conflict because the histogram-matching view changes the
        # default aggregation of the histogram to Sum aggregation which is the
        # same aggregation as the default aggregation of the up down counter
        # and also the temporality and monotonicity of the up down counter and
        # the histogram are the same.

        up_down_counter = _UpDownCounter(
            "up_down_counter",
            Mock(),
            [Mock()],
            unit="unit",
            description="description",
        )
        histogram = _Histogram(
            "histogram",
            Mock(),
            [Mock()],
            unit="unit",
            description="description",
        )
        metric_reader_storage = MetricReaderStorage(
            SdkConfiguration(
                exemplar_filter=Mock(),
                resource=Mock(),
                metric_readers=(),
                views=(
                    View(instrument_name="up_down_counter", name="foo"),
                    View(
                        instrument_name="histogram",
                        name="foo",
                        aggregation=SumAggregation(),
                    ),
                ),
            ),
            MagicMock(
                **{
                    "__getitem__.return_value": AggregationTemporality.CUMULATIVE
                }
            ),
            MagicMock(**{"__getitem__.return_value": DefaultAggregation()}),
        )

        with self.assertRaises(AssertionError):
            with self.assertLogs(level=WARNING):
                metric_reader_storage.consume_measurement(
                    Measurement(1, time_ns(), up_down_counter, Context())
                )

        with self.assertLogs(level=WARNING) as log:
            metric_reader_storage.consume_measurement(
                Measurement(1, time_ns(), histogram, Context())
            )

        self.assertIn(
            "will cause conflicting metrics",
            log.records[0].message,
        )
