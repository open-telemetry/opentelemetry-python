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

import concurrent.futures
import random
import unittest
from math import inf
from unittest import mock

from opentelemetry.context import get_value
from opentelemetry.sdk import metrics
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricsExporter,
    MetricRecord,
)
from opentelemetry.sdk.metrics.export.aggregate import (
    LastValueAggregator,
    MinMaxSumCountAggregator,
    SumAggregator,
    ValueObserverAggregator,
)
from opentelemetry.sdk.metrics.export.controller import PushController
from opentelemetry.sdk.metrics.export.processor import Processor
from opentelemetry.sdk.resources import Resource


# pylint: disable=protected-access
class TestConsoleMetricsExporter(unittest.TestCase):
    # pylint: disable=no-self-use
    def test_export(self):
        meter_provider = metrics.MeterProvider()
        meter = meter_provider.get_meter(__name__)
        exporter = ConsoleMetricsExporter()
        metric = metrics.Counter(
            "available memory",
            "available memory",
            "bytes",
            int,
            meter,
            ("environment",),
        )
        labels = {"environment": "staging"}
        aggregator = SumAggregator()
        record = MetricRecord(
            metric, labels, aggregator, meter_provider.resource
        )
        result = '{}(data="{}", labels="{}", value={}, resource={})'.format(
            ConsoleMetricsExporter.__name__,
            metric,
            labels,
            aggregator.checkpoint,
            meter_provider.resource.attributes,
        )
        with mock.patch("sys.stdout") as mock_stdout:
            exporter.export([record])
            mock_stdout.write.assert_any_call(result)


class TestProcessor(unittest.TestCase):
    def test_checkpoint_set(self):
        meter_provider = metrics.MeterProvider()
        meter = meter_provider.get_meter(__name__)
        processor = Processor(True, meter_provider.resource)
        aggregator = SumAggregator()
        metric = metrics.Counter(
            "available memory", "available memory", "bytes", int, meter
        )
        aggregator.update(1.0)
        labels = ()
        _batch_map = {}
        _batch_map[(metric, SumAggregator, tuple(), labels)] = aggregator
        processor._batch_map = _batch_map
        records = processor.checkpoint_set()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].instrument, metric)
        self.assertEqual(records[0].labels, labels)
        self.assertEqual(records[0].aggregator, aggregator)

    def test_checkpoint_set_empty(self):
        processor = Processor(True, Resource.create_empty())
        records = processor.checkpoint_set()
        self.assertEqual(len(records), 0)

    def test_finished_collection_stateless(self):
        meter_provider = metrics.MeterProvider()
        meter = meter_provider.get_meter(__name__)
        processor = Processor(False, meter_provider.resource)
        aggregator = SumAggregator()
        metric = metrics.Counter(
            "available memory", "available memory", "bytes", int, meter
        )
        aggregator.update(1.0)
        labels = ()
        _batch_map = {}
        _batch_map[(metric, SumAggregator, tuple(), labels)] = aggregator
        processor._batch_map = _batch_map
        processor.finished_collection()
        self.assertEqual(len(processor._batch_map), 0)

    def test_finished_collection_stateful(self):
        meter_provider = metrics.MeterProvider()
        meter = meter_provider.get_meter(__name__)
        processor = Processor(True, meter_provider.resource)
        aggregator = SumAggregator()
        metric = metrics.Counter(
            "available memory", "available memory", "bytes", int, meter
        )
        aggregator.update(1.0)
        labels = ()
        _batch_map = {}
        _batch_map[(metric, SumAggregator, tuple(), labels)] = aggregator
        processor._batch_map = _batch_map
        processor.finished_collection()
        self.assertEqual(len(processor._batch_map), 1)

    def test_processor_process_exists(self):
        meter_provider = metrics.MeterProvider()
        meter = meter_provider.get_meter(__name__)
        processor = Processor(True, meter_provider.resource)
        aggregator = SumAggregator()
        aggregator2 = SumAggregator()
        metric = metrics.Counter(
            "available memory", "available memory", "bytes", int, meter
        )
        labels = ()
        _batch_map = {}
        batch_key = (metric, SumAggregator, tuple(), labels)
        _batch_map[batch_key] = aggregator
        aggregator2.update(1.0)
        processor._batch_map = _batch_map
        record = metrics.Record(metric, labels, aggregator2)
        processor.process(record)
        self.assertEqual(len(processor._batch_map), 1)
        self.assertIsNotNone(processor._batch_map.get(batch_key))
        self.assertEqual(processor._batch_map.get(batch_key).current, 0)
        self.assertEqual(processor._batch_map.get(batch_key).checkpoint, 1.0)

    def test_processor_process_not_exists(self):
        meter_provider = metrics.MeterProvider()
        meter = meter_provider.get_meter(__name__)
        processor = Processor(True, meter_provider.resource)
        aggregator = SumAggregator()
        metric = metrics.Counter(
            "available memory", "available memory", "bytes", int, meter
        )
        labels = ()
        _batch_map = {}
        batch_key = (metric, SumAggregator, tuple(), labels)
        aggregator.update(1.0)
        processor._batch_map = _batch_map
        record = metrics.Record(metric, labels, aggregator)
        processor.process(record)
        self.assertEqual(len(processor._batch_map), 1)
        self.assertIsNotNone(processor._batch_map.get(batch_key))
        self.assertEqual(processor._batch_map.get(batch_key).current, 0)
        self.assertEqual(processor._batch_map.get(batch_key).checkpoint, 1.0)

    def test_processor_process_not_stateful(self):
        meter_provider = metrics.MeterProvider()
        processor = Processor(True, meter_provider.resource)
        aggregator = SumAggregator()
        metric = metrics.Counter(
            "available memory",
            "available memory",
            "bytes",
            int,
            meter_provider.get_meter(__name__),
        )
        labels = ()
        _batch_map = {}
        batch_key = (metric, SumAggregator, tuple(), labels)
        aggregator.update(1.0)
        processor._batch_map = _batch_map
        record = metrics.Record(metric, labels, aggregator)
        processor.process(record)
        self.assertEqual(len(processor._batch_map), 1)
        self.assertIsNotNone(processor._batch_map.get(batch_key))
        self.assertEqual(processor._batch_map.get(batch_key).current, 0)
        self.assertEqual(processor._batch_map.get(batch_key).checkpoint, 1.0)


class TestSumAggregator(unittest.TestCase):
    @staticmethod
    def call_update(sum_agg):
        update_total = 0
        for _ in range(0, 100000):
            val = random.getrandbits(32)
            sum_agg.update(val)
            update_total += val
        return update_total

    @mock.patch("opentelemetry.sdk.metrics.export.aggregate.time_ns")
    def test_update(self, time_mock):
        time_mock.return_value = 123
        sum_agg = SumAggregator()
        sum_agg.update(1.0)
        sum_agg.update(2.0)
        self.assertEqual(sum_agg.current, 3.0)
        self.assertEqual(sum_agg.last_update_timestamp, 123)

    def test_checkpoint(self):
        sum_agg = SumAggregator()
        sum_agg.update(2.0)
        sum_agg.take_checkpoint()
        self.assertEqual(sum_agg.current, 0)
        self.assertEqual(sum_agg.checkpoint, 2.0)

    def test_merge(self):
        sum_agg = SumAggregator()
        sum_agg2 = SumAggregator()
        sum_agg.checkpoint = 1.0
        sum_agg2.checkpoint = 3.0
        sum_agg2.last_update_timestamp = 123
        sum_agg.merge(sum_agg2)
        self.assertEqual(sum_agg.checkpoint, 4.0)
        self.assertEqual(sum_agg.last_update_timestamp, 123)

    def test_concurrent_update(self):
        sum_agg = SumAggregator()

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            fut1 = executor.submit(self.call_update, sum_agg)
            fut2 = executor.submit(self.call_update, sum_agg)

            updapte_total = fut1.result() + fut2.result()

        sum_agg.take_checkpoint()
        self.assertEqual(updapte_total, sum_agg.checkpoint)

    def test_concurrent_update_and_checkpoint(self):
        sum_agg = SumAggregator()
        checkpoint_total = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            fut = executor.submit(self.call_update, sum_agg)

            while not fut.done():
                sum_agg.take_checkpoint()
                checkpoint_total += sum_agg.checkpoint

        sum_agg.take_checkpoint()
        checkpoint_total += sum_agg.checkpoint

        self.assertEqual(fut.result(), checkpoint_total)


class TestMinMaxSumCountAggregator(unittest.TestCase):
    @staticmethod
    def call_update(mmsc):
        min_ = float("inf")
        max_ = float("-inf")
        sum_ = 0
        count_ = 0
        for _ in range(0, 100000):
            val = random.getrandbits(32)
            mmsc.update(val)
            if val < min_:
                min_ = val
            if val > max_:
                max_ = val
            sum_ += val
            count_ += 1
        return MinMaxSumCountAggregator._TYPE(min_, max_, sum_, count_)

    @mock.patch("opentelemetry.sdk.metrics.export.aggregate.time_ns")
    def test_update(self, time_mock):
        time_mock.return_value = 123
        mmsc = MinMaxSumCountAggregator()
        # test current values without any update
        self.assertEqual(mmsc.current, MinMaxSumCountAggregator._EMPTY)

        # call update with some values
        values = (3, 50, 3, 97)
        for val in values:
            mmsc.update(val)

        self.assertEqual(
            mmsc.current, (min(values), max(values), sum(values), len(values))
        )
        self.assertEqual(mmsc.last_update_timestamp, 123)

    def test_checkpoint(self):
        mmsc = MinMaxSumCountAggregator()

        # take checkpoint wihtout any update
        mmsc.take_checkpoint()
        self.assertEqual(mmsc.checkpoint, MinMaxSumCountAggregator._EMPTY)

        # call update with some values
        values = (3, 50, 3, 97)
        for val in values:
            mmsc.update(val)

        mmsc.take_checkpoint()
        self.assertEqual(
            mmsc.checkpoint,
            (min(values), max(values), sum(values), len(values)),
        )

        self.assertEqual(mmsc.current, MinMaxSumCountAggregator._EMPTY)

    def test_merge(self):
        mmsc1 = MinMaxSumCountAggregator()
        mmsc2 = MinMaxSumCountAggregator()

        checkpoint1 = MinMaxSumCountAggregator._TYPE(3, 150, 101, 3)
        checkpoint2 = MinMaxSumCountAggregator._TYPE(1, 33, 44, 2)

        mmsc1.checkpoint = checkpoint1
        mmsc2.checkpoint = checkpoint2

        mmsc1.last_update_timestamp = 100
        mmsc2.last_update_timestamp = 123

        mmsc1.merge(mmsc2)

        mmsc1_checkpoint = mmsc1.checkpoint
        mmsc1.checkpoint = checkpoint1
        mmsc2.checkpoint = checkpoint2

        mmsc1.merge(mmsc2)

        self.assertEqual(mmsc1_checkpoint, mmsc1.checkpoint)

        self.assertEqual(mmsc1.last_update_timestamp, 123)

    def test_merge_checkpoint(self):
        type_ = MinMaxSumCountAggregator._TYPE
        empty = MinMaxSumCountAggregator._EMPTY

        mmsc0 = MinMaxSumCountAggregator()
        mmsc1 = MinMaxSumCountAggregator()

        mmsc0.checkpoint = empty
        mmsc1.checkpoint = empty

        mmsc0.merge(mmsc1)
        self.assertEqual(mmsc0.checkpoint, mmsc1.checkpoint)

        mmsc0.checkpoint = empty
        mmsc1.checkpoint = type_(0, 0, 0, 0)

        mmsc0.merge(mmsc1)
        self.assertEqual(mmsc0.checkpoint, mmsc1.checkpoint)

        mmsc0.checkpoint = type_(0, 0, 0, 0)
        mmsc1.checkpoint = empty

        mmsc1.merge(mmsc0)
        self.assertEqual(mmsc1.checkpoint, mmsc0.checkpoint)

        mmsc0.checkpoint = type_(0, 0, 0, 0)
        mmsc1.checkpoint = type_(0, 0, 0, 0)

        mmsc0.merge(mmsc1)
        self.assertEqual(mmsc1.checkpoint, mmsc0.checkpoint)

        mmsc0.checkpoint = type_(44, 23, 55, 86)
        mmsc1.checkpoint = empty

        mmsc0.merge(mmsc1)
        self.assertEqual(mmsc0.checkpoint, type_(44, 23, 55, 86))

        mmsc0.checkpoint = type_(3, 150, 101, 3)
        mmsc1.checkpoint = type_(1, 33, 44, 2)

        mmsc0.merge(mmsc1)
        self.assertEqual(mmsc0.checkpoint, type_(1, 150, 101 + 44, 2 + 3))

    def test_merge_with_empty(self):
        mmsc1 = MinMaxSumCountAggregator()
        mmsc2 = MinMaxSumCountAggregator()

        checkpoint1 = MinMaxSumCountAggregator._TYPE(3, 150, 101, 3)
        mmsc1.checkpoint = checkpoint1

        mmsc1.merge(mmsc2)

        self.assertEqual(mmsc1.checkpoint, checkpoint1)

    def test_concurrent_update(self):
        mmsc0 = MinMaxSumCountAggregator()
        mmsc1 = MinMaxSumCountAggregator()

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            mmsc0.checkpoint = ex.submit(self.call_update, mmsc0).result()
            mmsc1.checkpoint = ex.submit(self.call_update, mmsc0).result()

            mmsc0.merge(mmsc1)

            mmsc0_checkpoint = mmsc0.checkpoint

            mmsc0.take_checkpoint()

            self.assertEqual(mmsc0_checkpoint, mmsc0.checkpoint)
            self.assertIsNot(mmsc0_checkpoint, mmsc0.checkpoint)

    def test_concurrent_update_and_checkpoint(self):
        mmsc0 = MinMaxSumCountAggregator()
        mmsc1 = MinMaxSumCountAggregator()
        mmsc1.checkpoint = MinMaxSumCountAggregator._TYPE(2 ** 32, 0, 0, 0)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(self.call_update, mmsc0)

            while not fut.done():
                mmsc0.take_checkpoint()
                mmsc0.merge(mmsc1)
                mmsc1.checkpoint = mmsc0.checkpoint

            mmsc0.take_checkpoint()
            mmsc0.merge(mmsc1)

            self.assertEqual(mmsc0.checkpoint, fut.result())


class TestValueObserverAggregator(unittest.TestCase):
    @mock.patch("opentelemetry.sdk.metrics.export.aggregate.time_ns")
    def test_update(self, time_mock):
        time_mock.return_value = 123
        observer = ValueObserverAggregator()
        # test current values without any update
        self.assertEqual(observer.mmsc.current, (inf, -inf, 0, 0))
        self.assertIsNone(observer.current)

        # call update with some values
        values = (3, 50, 3, 97, 27)
        for val in values:
            observer.update(val)

        self.assertEqual(
            observer.mmsc.current,
            (min(values), max(values), sum(values), len(values)),
        )
        self.assertEqual(observer.last_update_timestamp, 123)

        self.assertEqual(observer.current, values[-1])

    def test_checkpoint(self):
        observer = ValueObserverAggregator()

        # take checkpoint wihtout any update
        observer.take_checkpoint()
        self.assertEqual(observer.checkpoint, (inf, -inf, 0, 0, None))

        # call update with some values
        values = (3, 50, 3, 97)
        for val in values:
            observer.update(val)

        observer.take_checkpoint()
        self.assertEqual(
            observer.checkpoint,
            (min(values), max(values), sum(values), len(values), values[-1]),
        )

    def test_merge(self):
        observer1 = ValueObserverAggregator()
        observer2 = ValueObserverAggregator()

        mmsc_checkpoint1 = MinMaxSumCountAggregator._TYPE(3, 150, 101, 3)
        mmsc_checkpoint2 = MinMaxSumCountAggregator._TYPE(1, 33, 44, 2)

        checkpoint1 = ValueObserverAggregator._TYPE(
            *(mmsc_checkpoint1 + (23,))
        )

        checkpoint2 = ValueObserverAggregator._TYPE(
            *(mmsc_checkpoint2 + (27,))
        )

        observer1.mmsc.checkpoint = mmsc_checkpoint1
        observer2.mmsc.checkpoint = mmsc_checkpoint2

        observer1.last_update_timestamp = 100
        observer2.last_update_timestamp = 123

        observer1.checkpoint = checkpoint1
        observer2.checkpoint = checkpoint2

        observer1.merge(observer2)

        self.assertEqual(
            observer1.checkpoint,
            (
                min(checkpoint1.min, checkpoint2.min),
                max(checkpoint1.max, checkpoint2.max),
                checkpoint1.sum + checkpoint2.sum,
                checkpoint1.count + checkpoint2.count,
                checkpoint2.last,
            ),
        )
        self.assertEqual(observer1.last_update_timestamp, 123)

    def test_merge_last_updated(self):
        observer1 = ValueObserverAggregator()
        observer2 = ValueObserverAggregator()

        mmsc_checkpoint1 = MinMaxSumCountAggregator._TYPE(3, 150, 101, 3)
        mmsc_checkpoint2 = MinMaxSumCountAggregator._TYPE(1, 33, 44, 2)

        checkpoint1 = ValueObserverAggregator._TYPE(
            *(mmsc_checkpoint1 + (23,))
        )

        checkpoint2 = ValueObserverAggregator._TYPE(
            *(mmsc_checkpoint2 + (27,))
        )

        observer1.mmsc.checkpoint = mmsc_checkpoint1
        observer2.mmsc.checkpoint = mmsc_checkpoint2

        observer1.last_update_timestamp = 123
        observer2.last_update_timestamp = 100

        observer1.checkpoint = checkpoint1
        observer2.checkpoint = checkpoint2

        observer1.merge(observer2)

        self.assertEqual(
            observer1.checkpoint,
            (
                min(checkpoint1.min, checkpoint2.min),
                max(checkpoint1.max, checkpoint2.max),
                checkpoint1.sum + checkpoint2.sum,
                checkpoint1.count + checkpoint2.count,
                checkpoint1.last,
            ),
        )
        self.assertEqual(observer1.last_update_timestamp, 123)

    def test_merge_last_updated_none(self):
        observer1 = ValueObserverAggregator()
        observer2 = ValueObserverAggregator()

        mmsc_checkpoint1 = MinMaxSumCountAggregator._TYPE(3, 150, 101, 3)
        mmsc_checkpoint2 = MinMaxSumCountAggregator._TYPE(1, 33, 44, 2)

        checkpoint1 = ValueObserverAggregator._TYPE(
            *(mmsc_checkpoint1 + (23,))
        )

        checkpoint2 = ValueObserverAggregator._TYPE(
            *(mmsc_checkpoint2 + (27,))
        )

        observer1.mmsc.checkpoint = mmsc_checkpoint1
        observer2.mmsc.checkpoint = mmsc_checkpoint2

        observer1.last_update_timestamp = 0
        observer2.last_update_timestamp = 100

        observer1.checkpoint = checkpoint1
        observer2.checkpoint = checkpoint2

        observer1.merge(observer2)

        self.assertEqual(
            observer1.checkpoint,
            (
                min(checkpoint1.min, checkpoint2.min),
                max(checkpoint1.max, checkpoint2.max),
                checkpoint1.sum + checkpoint2.sum,
                checkpoint1.count + checkpoint2.count,
                checkpoint2.last,
            ),
        )
        self.assertEqual(observer1.last_update_timestamp, 100)

    def test_merge_with_empty(self):
        observer1 = ValueObserverAggregator()
        observer2 = ValueObserverAggregator()

        mmsc_checkpoint1 = MinMaxSumCountAggregator._TYPE(3, 150, 101, 3)
        checkpoint1 = ValueObserverAggregator._TYPE(
            *(mmsc_checkpoint1 + (23,))
        )

        observer1.mmsc.checkpoint = mmsc_checkpoint1
        observer1.checkpoint = checkpoint1
        observer1.last_update_timestamp = 100

        observer1.merge(observer2)

        self.assertEqual(observer1.checkpoint, checkpoint1)


class TestLastValueAggregator(unittest.TestCase):
    @mock.patch("opentelemetry.sdk.metrics.export.aggregate.time_ns")
    def test_update(self, time_mock):
        time_mock.return_value = 123
        observer = LastValueAggregator()
        # test current values without any update
        self.assertIsNone(observer.current)

        # call update with some values
        values = (3, 50, 3, 97, 27)
        for val in values:
            observer.update(val)

        self.assertEqual(observer.last_update_timestamp, 123)
        self.assertEqual(observer.current, values[-1])

    def test_checkpoint(self):
        observer = LastValueAggregator()

        # take checkpoint without any update
        observer.take_checkpoint()
        self.assertEqual(observer.checkpoint, None)

        # call update with some values
        values = (3, 50, 3, 97)
        for val in values:
            observer.update(val)

        observer.take_checkpoint()
        self.assertEqual(observer.checkpoint, 97)

    def test_merge(self):
        observer1 = LastValueAggregator()
        observer2 = LastValueAggregator()

        observer1.checkpoint = 23
        observer2.checkpoint = 47

        observer1.last_update_timestamp = 100
        observer2.last_update_timestamp = 123

        observer1.merge(observer2)

        self.assertEqual(observer1.checkpoint, 47)
        self.assertEqual(observer1.last_update_timestamp, 123)

    def test_merge_last_updated(self):
        observer1 = LastValueAggregator()
        observer2 = LastValueAggregator()

        observer1.checkpoint = 23
        observer2.checkpoint = 47

        observer1.last_update_timestamp = 123
        observer2.last_update_timestamp = 100

        observer1.merge(observer2)

        self.assertEqual(observer1.checkpoint, 23)
        self.assertEqual(observer1.last_update_timestamp, 123)

    def test_merge_last_updated_none(self):
        observer1 = LastValueAggregator()
        observer2 = LastValueAggregator()

        observer1.checkpoint = 23
        observer2.checkpoint = 47

        observer1.last_update_timestamp = 0
        observer2.last_update_timestamp = 100

        observer1.merge(observer2)

        self.assertEqual(observer1.checkpoint, 47)
        self.assertEqual(observer1.last_update_timestamp, 100)

    def test_merge_with_empty(self):
        observer1 = LastValueAggregator()
        observer2 = LastValueAggregator()

        observer1.checkpoint = 23
        observer1.last_update_timestamp = 100

        observer1.merge(observer2)

        self.assertEqual(observer1.checkpoint, 23)
        self.assertEqual(observer1.last_update_timestamp, 100)


class TestController(unittest.TestCase):
    def test_push_controller(self):
        meter = mock.Mock()
        exporter = mock.Mock()
        controller = PushController(meter, exporter, 5.0)
        meter.collect.assert_not_called()
        exporter.export.assert_not_called()

        controller.shutdown()
        self.assertTrue(controller.finished.isSet())

        # shutdown should flush the meter
        self.assertEqual(meter.collect.call_count, 1)
        self.assertEqual(exporter.export.call_count, 1)

    def test_push_controller_suppress_instrumentation(self):
        meter = mock.Mock()
        exporter = mock.Mock()
        exporter.export = lambda x: self.assertIsNotNone(
            get_value("suppress_instrumentation")
        )
        with mock.patch(
            "opentelemetry.context._RUNTIME_CONTEXT"
        ) as context_patch:
            controller = PushController(meter, exporter, 30.0)
            controller.tick()
            self.assertEqual(context_patch.attach.called, True)
            self.assertEqual(context_patch.detach.called, True)
        self.assertEqual(get_value("suppress_instrumentation"), None)
