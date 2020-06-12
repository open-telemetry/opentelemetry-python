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
from unittest import mock

from opentelemetry.context import get_value
from opentelemetry.sdk import metrics
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricsExporter,
    MetricRecord,
)
from opentelemetry.sdk.metrics.export.aggregate import (
    CounterAggregator,
    MinMaxSumCountAggregator,
    ValueObserverAggregator,
)
from opentelemetry.sdk.metrics.export.batcher import UngroupedBatcher
from opentelemetry.sdk.metrics.export.controller import PushController


# pylint: disable=protected-access
class TestConsoleMetricsExporter(unittest.TestCase):
    # pylint: disable=no-self-use
    def test_export(self):
        meter = metrics.MeterProvider().get_meter(__name__)
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
        aggregator = CounterAggregator()
        record = MetricRecord(metric, labels, aggregator)
        result = '{}(data="{}", labels="{}", value={})'.format(
            ConsoleMetricsExporter.__name__,
            metric,
            labels,
            aggregator.checkpoint,
        )
        with mock.patch("sys.stdout") as mock_stdout:
            exporter.export([record])
            mock_stdout.write.assert_any_call(result)


class TestBatcher(unittest.TestCase):
    def test_aggregator_for_counter(self):
        batcher = UngroupedBatcher(True)
        self.assertTrue(
            isinstance(
                batcher.aggregator_for(metrics.Counter), CounterAggregator
            )
        )

    def test_aggregator_for_updowncounter(self):
        batcher = UngroupedBatcher(True)
        self.assertTrue(
            isinstance(
                batcher.aggregator_for(metrics.UpDownCounter),
                CounterAggregator,
            )
        )

    # TODO: Add other aggregator tests

    def test_checkpoint_set(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        batcher = UngroupedBatcher(True)
        aggregator = CounterAggregator()
        metric = metrics.Counter(
            "available memory",
            "available memory",
            "bytes",
            int,
            meter,
            ("environment",),
        )
        aggregator.update(1.0)
        labels = ()
        _batch_map = {}
        _batch_map[(metric, labels)] = aggregator
        batcher._batch_map = _batch_map
        records = batcher.checkpoint_set()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].instrument, metric)
        self.assertEqual(records[0].labels, labels)
        self.assertEqual(records[0].aggregator, aggregator)

    def test_checkpoint_set_empty(self):
        batcher = UngroupedBatcher(True)
        records = batcher.checkpoint_set()
        self.assertEqual(len(records), 0)

    def test_finished_collection_stateless(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        batcher = UngroupedBatcher(False)
        aggregator = CounterAggregator()
        metric = metrics.Counter(
            "available memory",
            "available memory",
            "bytes",
            int,
            meter,
            ("environment",),
        )
        aggregator.update(1.0)
        labels = ()
        _batch_map = {}
        _batch_map[(metric, labels)] = aggregator
        batcher._batch_map = _batch_map
        batcher.finished_collection()
        self.assertEqual(len(batcher._batch_map), 0)

    def test_finished_collection_stateful(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        batcher = UngroupedBatcher(True)
        aggregator = CounterAggregator()
        metric = metrics.Counter(
            "available memory",
            "available memory",
            "bytes",
            int,
            meter,
            ("environment",),
        )
        aggregator.update(1.0)
        labels = ()
        _batch_map = {}
        _batch_map[(metric, labels)] = aggregator
        batcher._batch_map = _batch_map
        batcher.finished_collection()
        self.assertEqual(len(batcher._batch_map), 1)

    # TODO: Abstract the logic once other batchers implemented
    def test_ungrouped_batcher_process_exists(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        batcher = UngroupedBatcher(True)
        aggregator = CounterAggregator()
        aggregator2 = CounterAggregator()
        metric = metrics.Counter(
            "available memory",
            "available memory",
            "bytes",
            int,
            meter,
            ("environment",),
        )
        labels = ()
        _batch_map = {}
        _batch_map[(metric, labels)] = aggregator
        aggregator2.update(1.0)
        batcher._batch_map = _batch_map
        record = metrics.Record(metric, labels, aggregator2)
        batcher.process(record)
        self.assertEqual(len(batcher._batch_map), 1)
        self.assertIsNotNone(batcher._batch_map.get((metric, labels)))
        self.assertEqual(batcher._batch_map.get((metric, labels)).current, 0)
        self.assertEqual(
            batcher._batch_map.get((metric, labels)).checkpoint, 1.0
        )

    def test_ungrouped_batcher_process_not_exists(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        batcher = UngroupedBatcher(True)
        aggregator = CounterAggregator()
        metric = metrics.Counter(
            "available memory",
            "available memory",
            "bytes",
            int,
            meter,
            ("environment",),
        )
        labels = ()
        _batch_map = {}
        aggregator.update(1.0)
        batcher._batch_map = _batch_map
        record = metrics.Record(metric, labels, aggregator)
        batcher.process(record)
        self.assertEqual(len(batcher._batch_map), 1)
        self.assertIsNotNone(batcher._batch_map.get((metric, labels)))
        self.assertEqual(batcher._batch_map.get((metric, labels)).current, 0)
        self.assertEqual(
            batcher._batch_map.get((metric, labels)).checkpoint, 1.0
        )

    def test_ungrouped_batcher_process_not_stateful(self):
        meter = metrics.MeterProvider().get_meter(__name__)
        batcher = UngroupedBatcher(True)
        aggregator = CounterAggregator()
        metric = metrics.Counter(
            "available memory",
            "available memory",
            "bytes",
            int,
            meter,
            ("environment",),
        )
        labels = ()
        _batch_map = {}
        aggregator.update(1.0)
        batcher._batch_map = _batch_map
        record = metrics.Record(metric, labels, aggregator)
        batcher.process(record)
        self.assertEqual(len(batcher._batch_map), 1)
        self.assertIsNotNone(batcher._batch_map.get((metric, labels)))
        self.assertEqual(batcher._batch_map.get((metric, labels)).current, 0)
        self.assertEqual(
            batcher._batch_map.get((metric, labels)).checkpoint, 1.0
        )


class TestCounterAggregator(unittest.TestCase):
    @staticmethod
    def call_update(counter):
        update_total = 0
        for _ in range(0, 100000):
            val = random.getrandbits(32)
            counter.update(val)
            update_total += val
        return update_total

    @mock.patch("opentelemetry.sdk.metrics.export.aggregate.time_ns")
    def test_update(self, time_mock):
        time_mock.return_value = 123
        counter = CounterAggregator()
        counter.update(1.0)
        counter.update(2.0)
        self.assertEqual(counter.current, 3.0)
        self.assertEqual(counter.last_update_timestamp, 123)

    def test_checkpoint(self):
        counter = CounterAggregator()
        counter.update(2.0)
        counter.take_checkpoint()
        self.assertEqual(counter.current, 0)
        self.assertEqual(counter.checkpoint, 2.0)

    def test_merge(self):
        counter = CounterAggregator()
        counter2 = CounterAggregator()
        counter.checkpoint = 1.0
        counter2.checkpoint = 3.0
        counter2.last_update_timestamp = 123
        counter.merge(counter2)
        self.assertEqual(counter.checkpoint, 4.0)
        self.assertEqual(counter.last_update_timestamp, 123)

    def test_concurrent_update(self):
        counter = CounterAggregator()

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            fut1 = executor.submit(self.call_update, counter)
            fut2 = executor.submit(self.call_update, counter)

            updapte_total = fut1.result() + fut2.result()

        counter.take_checkpoint()
        self.assertEqual(updapte_total, counter.checkpoint)

    def test_concurrent_update_and_checkpoint(self):
        counter = CounterAggregator()
        checkpoint_total = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            fut = executor.submit(self.call_update, counter)

            while not fut.done():
                counter.take_checkpoint()
                checkpoint_total += counter.checkpoint

        counter.take_checkpoint()
        checkpoint_total += counter.checkpoint

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

        self.assertEqual(
            mmsc1.checkpoint,
            MinMaxSumCountAggregator._merge_checkpoint(
                checkpoint1, checkpoint2
            ),
        )
        self.assertEqual(mmsc1.last_update_timestamp, 123)

    def test_merge_checkpoint(self):
        func = MinMaxSumCountAggregator._merge_checkpoint
        _type = MinMaxSumCountAggregator._TYPE
        empty = MinMaxSumCountAggregator._EMPTY

        ret = func(empty, empty)
        self.assertEqual(ret, empty)

        ret = func(empty, _type(0, 0, 0, 0))
        self.assertEqual(ret, _type(0, 0, 0, 0))

        ret = func(_type(0, 0, 0, 0), empty)
        self.assertEqual(ret, _type(0, 0, 0, 0))

        ret = func(_type(0, 0, 0, 0), _type(0, 0, 0, 0))
        self.assertEqual(ret, _type(0, 0, 0, 0))

        ret = func(_type(44, 23, 55, 86), empty)
        self.assertEqual(ret, _type(44, 23, 55, 86))

        ret = func(_type(3, 150, 101, 3), _type(1, 33, 44, 2))
        self.assertEqual(ret, _type(1, 150, 101 + 44, 2 + 3))

    def test_merge_with_empty(self):
        mmsc1 = MinMaxSumCountAggregator()
        mmsc2 = MinMaxSumCountAggregator()

        checkpoint1 = MinMaxSumCountAggregator._TYPE(3, 150, 101, 3)
        mmsc1.checkpoint = checkpoint1

        mmsc1.merge(mmsc2)

        self.assertEqual(mmsc1.checkpoint, checkpoint1)

    def test_concurrent_update(self):
        mmsc = MinMaxSumCountAggregator()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            fut1 = ex.submit(self.call_update, mmsc)
            fut2 = ex.submit(self.call_update, mmsc)

            ret1 = fut1.result()
            ret2 = fut2.result()

            update_total = MinMaxSumCountAggregator._merge_checkpoint(
                ret1, ret2
            )
            mmsc.take_checkpoint()

            self.assertEqual(update_total, mmsc.checkpoint)

    def test_concurrent_update_and_checkpoint(self):
        mmsc = MinMaxSumCountAggregator()
        checkpoint_total = MinMaxSumCountAggregator._TYPE(2 ** 32, 0, 0, 0)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(self.call_update, mmsc)

            while not fut.done():
                mmsc.take_checkpoint()
                checkpoint_total = MinMaxSumCountAggregator._merge_checkpoint(
                    checkpoint_total, mmsc.checkpoint
                )

            mmsc.take_checkpoint()
            checkpoint_total = MinMaxSumCountAggregator._merge_checkpoint(
                checkpoint_total, mmsc.checkpoint
            )

            self.assertEqual(checkpoint_total, fut.result())


class TestValueObserverAggregator(unittest.TestCase):
    @mock.patch("opentelemetry.sdk.metrics.export.aggregate.time_ns")
    def test_update(self, time_mock):
        time_mock.return_value = 123
        observer = ValueObserverAggregator()
        # test current values without any update
        self.assertEqual(observer.mmsc.current, (None, None, None, 0))
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
        self.assertEqual(observer.checkpoint, (None, None, None, 0, None))

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

        observer1.last_update_timestamp = None
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
