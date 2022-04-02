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

from unittest.mock import Mock, patch

from opentelemetry.sdk._metrics.aggregation import DropAggregation
from opentelemetry.sdk._metrics.instrument import Counter
from opentelemetry.sdk._metrics.measurement import Measurement
from opentelemetry.sdk._metrics.metric_reader_storage import (
    MetricReaderStorage,
)
from opentelemetry.sdk._metrics.point import AggregationTemporality
from opentelemetry.sdk._metrics.sdk_configuration import SdkConfiguration
from opentelemetry.sdk._metrics.view import View
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
        "opentelemetry.sdk._metrics.metric_reader_storage._ViewInstrumentMatch"
    )
    def test_creates_view_instrument_matches(
        self, MockViewInstrumentMatch: Mock
    ):
        """It should create a MockViewInstrumentMatch when an instrument matches a view"""
        instrument1 = Mock(name="instrument1")
        instrument2 = Mock(name="instrument2")

        view1 = mock_view_matching("view_1", instrument1)
        view2 = mock_view_matching("view_2", instrument1, instrument2)
        storage = MetricReaderStorage(
            SdkConfiguration(
                resource=Mock(),
                metric_readers=(),
                views=(view1, view2),
            )
        )

        # instrument1 matches view1 and view2, so should create two ViewInstrumentMatch objects
        storage.consume_measurement(Measurement(1, instrument1))
        self.assertEqual(
            len(MockViewInstrumentMatch.call_args_list),
            2,
            MockViewInstrumentMatch.mock_calls,
        )
        # they should only be created the first time the instrument is seen
        storage.consume_measurement(Measurement(1, instrument1))
        self.assertEqual(len(MockViewInstrumentMatch.call_args_list), 2)

        # instrument2 matches view2, so should create a single ViewInstrumentMatch
        MockViewInstrumentMatch.call_args_list.clear()
        storage.consume_measurement(Measurement(1, instrument2))
        self.assertEqual(len(MockViewInstrumentMatch.call_args_list), 1)

    @patch(
        "opentelemetry.sdk._metrics.metric_reader_storage._ViewInstrumentMatch"
    )
    def test_forwards_calls_to_view_instrument_match(
        self, MockViewInstrumentMatch: Mock
    ):
        view_instrument_match1 = Mock()
        view_instrument_match2 = Mock()
        view_instrument_match3 = Mock()
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
                resource=Mock(),
                metric_readers=(),
                views=(view1, view2),
            )
        )

        # Measurements from an instrument should be passed on to each ViewInstrumentMatch objects
        # created for that instrument
        measurement = Measurement(1, instrument1)
        storage.consume_measurement(measurement)
        view_instrument_match1.consume_measurement.assert_called_once_with(
            measurement
        )
        view_instrument_match2.consume_measurement.assert_called_once_with(
            measurement
        )
        view_instrument_match3.consume_measurement.assert_not_called()

        measurement = Measurement(1, instrument2)
        storage.consume_measurement(measurement)
        view_instrument_match3.consume_measurement.assert_called_once_with(
            measurement
        )

        # collect() should call collect on all of its _ViewInstrumentMatch objects and combine them together
        all_metrics = [Mock() for _ in range(6)]
        view_instrument_match1.collect.return_value = all_metrics[:2]
        view_instrument_match2.collect.return_value = all_metrics[2:4]
        view_instrument_match3.collect.return_value = all_metrics[4:]

        result = storage.collect(AggregationTemporality.CUMULATIVE)
        view_instrument_match1.collect.assert_called_once()
        view_instrument_match2.collect.assert_called_once()
        view_instrument_match3.collect.assert_called_once()
        self.assertEqual(result, all_metrics)

    @patch(
        "opentelemetry.sdk._metrics.metric_reader_storage._ViewInstrumentMatch"
    )
    def test_race_concurrent_measurements(self, MockViewInstrumentMatch: Mock):
        mock_view_instrument_match_ctor = MockFunc()
        MockViewInstrumentMatch.side_effect = mock_view_instrument_match_ctor

        instrument1 = Mock(name="instrument1")
        view1 = mock_view_matching(instrument1)
        storage = MetricReaderStorage(
            SdkConfiguration(
                resource=Mock(),
                metric_readers=(),
                views=(view1,),
            )
        )

        def send_measurement():
            storage.consume_measurement(Measurement(1, instrument1))

        # race sending many measurements concurrently
        self.run_with_many_threads(send_measurement)

        # _ViewInstrumentMatch constructor should have only been called once
        self.assertEqual(mock_view_instrument_match_ctor.call_count, 1)

    @patch(
        "opentelemetry.sdk._metrics.metric_reader_storage._ViewInstrumentMatch"
    )
    def test_default_view_enabled(self, MockViewInstrumentMatch: Mock):
        """Instruments should be matched with default views when enabled"""
        instrument1 = Mock(name="instrument1")
        instrument2 = Mock(name="instrument2")

        storage = MetricReaderStorage(
            SdkConfiguration(
                resource=Mock(),
                metric_readers=(),
                views=(),
            )
        )

        storage.consume_measurement(Measurement(1, instrument1))
        self.assertEqual(
            len(MockViewInstrumentMatch.call_args_list),
            1,
            MockViewInstrumentMatch.mock_calls,
        )
        storage.consume_measurement(Measurement(1, instrument1))
        self.assertEqual(len(MockViewInstrumentMatch.call_args_list), 1)

        MockViewInstrumentMatch.call_args_list.clear()
        storage.consume_measurement(Measurement(1, instrument2))
        self.assertEqual(len(MockViewInstrumentMatch.call_args_list), 1)

    def test_drop_aggregation(self):

        counter = Counter("name", Mock(), Mock())
        metric_reader_storage = MetricReaderStorage(
            SdkConfiguration(
                resource=Mock(),
                metric_readers=(),
                views=(
                    View(
                        instrument_name="name", aggregation=DropAggregation()
                    ),
                ),
            )
        )
        metric_reader_storage.consume_measurement(Measurement(1, counter))

        self.assertEqual(
            [], metric_reader_storage.collect(AggregationTemporality.DELTA)
        )
