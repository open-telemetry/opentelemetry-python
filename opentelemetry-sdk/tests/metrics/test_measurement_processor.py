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

import unittest
from time import time_ns
from unittest.mock import Mock

from opentelemetry.context import get_current
from opentelemetry.sdk.metrics._internal.measurement import Measurement
from opentelemetry.sdk.metrics._internal.measurement_processor import (
    AttributeFilterMeasurementProcessor,
    BaggageMeasurementProcessor,
    MeasurementProcessor,
    MeasurementProcessorChain,
    NoOpMeasurementProcessor,
    StaticAttributeMeasurementProcessor,
    ValueRangeMeasurementProcessor,
)


class TestMeasurementProcessorChain(unittest.TestCase):
    def test_empty_chain(self):
        """Test that an empty chain uses NoOpMeasurementProcessor."""
        chain = MeasurementProcessorChain()
        final_consumer = Mock()
        measurement = Measurement(
            value=1.0,
            time_unix_nano=time_ns(),
            instrument=Mock(),
            context=get_current(),
            attributes={"test": "value"},
        )

        chain.process(measurement, final_consumer)
        final_consumer.assert_called_once_with(measurement)

    def test_single_processor(self):
        """Test chain with a single processor."""
        processor = Mock(spec=MeasurementProcessor)
        chain = MeasurementProcessorChain([processor])
        final_consumer = Mock()
        measurement = Measurement(
            value=1.0,
            time_unix_nano=time_ns(),
            instrument=Mock(),
            context=get_current(),
            attributes={"test": "value"},
        )

        # Configure the processor to call next_processor
        def mock_process(m, next_proc):
            next_proc(m)

        processor.process.side_effect = mock_process

        chain.process(measurement, final_consumer)
        processor.process.assert_called_once()
        final_consumer.assert_called_once_with(measurement)

    def test_multiple_processors(self):
        """Test chain with multiple processors."""
        processor1 = Mock(spec=MeasurementProcessor)
        processor2 = Mock(spec=MeasurementProcessor)
        chain = MeasurementProcessorChain([processor1, processor2])
        final_consumer = Mock()
        measurement = Measurement(
            value=1.0,
            time_unix_nano=time_ns(),
            instrument=Mock(),
            context=get_current(),
            attributes={"test": "value"},
        )

        # Configure processors to call next_processor
        def mock_process1(m, next_proc):
            next_proc(m)

        def mock_process2(m, next_proc):
            next_proc(m)

        processor1.process.side_effect = mock_process1
        processor2.process.side_effect = mock_process2

        chain.process(measurement, final_consumer)
        processor1.process.assert_called_once()
        processor2.process.assert_called_once()
        final_consumer.assert_called_once_with(measurement)


class TestNoOpMeasurementProcessor(unittest.TestCase):
    def test_no_op_processor(self):
        """Test that NoOpMeasurementProcessor passes measurements through unchanged."""
        processor = NoOpMeasurementProcessor()
        next_processor = Mock()
        measurement = Measurement(
            value=1.0,
            time_unix_nano=time_ns(),
            instrument=Mock(),
            context=get_current(),
            attributes={"test": "value"},
        )

        processor.process(measurement, next_processor)
        next_processor.assert_called_once_with(measurement)


class TestStaticAttributeMeasurementProcessor(unittest.TestCase):
    def test_add_static_attributes(self):
        """Test adding static attributes to measurements."""
        static_attrs = {"environment": "test", "version": "1.0"}
        processor = StaticAttributeMeasurementProcessor(static_attrs)
        next_processor = Mock()
        measurement = Measurement(
            value=1.0,
            time_unix_nano=time_ns(),
            instrument=Mock(),
            context=get_current(),
            attributes={"original": "value"},
        )

        processor.process(measurement, next_processor)

        # Check that next_processor was called with modified measurement
        next_processor.assert_called_once()
        modified_measurement = next_processor.call_args[0][0]

        # Should have both original and static attributes
        expected_attrs = {
            "original": "value",
            "environment": "test",
            "version": "1.0",
        }
        self.assertEqual(modified_measurement.attributes, expected_attrs)

    def test_empty_static_attributes(self):
        """Test with empty static attributes."""
        processor = StaticAttributeMeasurementProcessor({})
        next_processor = Mock()
        measurement = Measurement(
            value=1.0,
            time_unix_nano=time_ns(),
            instrument=Mock(),
            context=get_current(),
            attributes={"original": "value"},
        )

        processor.process(measurement, next_processor)
        next_processor.assert_called_once_with(measurement)


class TestAttributeFilterMeasurementProcessor(unittest.TestCase):
    def test_filter_attributes(self):
        """Test filtering out specific attributes."""
        processor = AttributeFilterMeasurementProcessor(
            ["sensitive", "internal"]
        )
        next_processor = Mock()
        measurement = Measurement(
            value=1.0,
            time_unix_nano=time_ns(),
            instrument=Mock(),
            context=get_current(),
            attributes={
                "keep": "value",
                "sensitive": "secret",
                "internal": "data",
                "also_keep": "another",
            },
        )

        processor.process(measurement, next_processor)

        # Check that next_processor was called with filtered measurement
        next_processor.assert_called_once()
        modified_measurement = next_processor.call_args[0][0]

        # Should only have non-filtered attributes
        expected_attrs = {"keep": "value", "also_keep": "another"}
        self.assertEqual(modified_measurement.attributes, expected_attrs)

    def test_no_attributes_to_filter(self):
        """Test with no attributes to filter."""
        processor = AttributeFilterMeasurementProcessor(["nonexistent"])
        next_processor = Mock()
        measurement = Measurement(
            value=1.0,
            time_unix_nano=time_ns(),
            instrument=Mock(),
            context=get_current(),
            attributes={"keep": "value"},
        )

        processor.process(measurement, next_processor)

        # Should keep original attributes
        next_processor.assert_called_once()
        modified_measurement = next_processor.call_args[0][0]
        self.assertEqual(modified_measurement.attributes, {"keep": "value"})


class TestValueRangeMeasurementProcessor(unittest.TestCase):
    def test_value_in_range(self):
        """Test that values in range are passed through."""
        processor = ValueRangeMeasurementProcessor(min_value=0, max_value=100)
        next_processor = Mock()
        measurement = Measurement(
            value=50.0,
            time_unix_nano=time_ns(),
            instrument=Mock(),
            context=get_current(),
            attributes={"test": "value"},
        )

        processor.process(measurement, next_processor)
        next_processor.assert_called_once_with(measurement)

    def test_value_below_min(self):
        """Test that values below minimum are dropped."""
        processor = ValueRangeMeasurementProcessor(min_value=0, max_value=100)
        next_processor = Mock()
        measurement = Measurement(
            value=-10.0,
            time_unix_nano=time_ns(),
            instrument=Mock(),
            context=get_current(),
            attributes={"test": "value"},
        )

        processor.process(measurement, next_processor)
        next_processor.assert_not_called()

    def test_value_above_max(self):
        """Test that values above maximum are dropped."""
        processor = ValueRangeMeasurementProcessor(min_value=0, max_value=100)
        next_processor = Mock()
        measurement = Measurement(
            value=150.0,
            time_unix_nano=time_ns(),
            instrument=Mock(),
            context=get_current(),
            attributes={"test": "value"},
        )

        processor.process(measurement, next_processor)
        next_processor.assert_not_called()

    def test_no_limits(self):
        """Test with no minimum or maximum limits."""
        processor = ValueRangeMeasurementProcessor()
        next_processor = Mock()
        measurement = Measurement(
            value=999999.0,
            time_unix_nano=time_ns(),
            instrument=Mock(),
            context=get_current(),
            attributes={"test": "value"},
        )

        processor.process(measurement, next_processor)
        next_processor.assert_called_once_with(measurement)


class TestBaggageMeasurementProcessor(unittest.TestCase):
    def test_no_baggage(self):
        """Test with no baggage in context."""
        processor = BaggageMeasurementProcessor()
        next_processor = Mock()
        measurement = Measurement(
            value=1.0,
            time_unix_nano=time_ns(),
            instrument=Mock(),
            context=get_current(),
            attributes={"test": "value"},
        )

        processor.process(measurement, next_processor)
        next_processor.assert_called_once_with(measurement)


if __name__ == "__main__":
    unittest.main()
