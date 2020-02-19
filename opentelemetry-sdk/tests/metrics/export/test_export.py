# Copyright 2019, OpenTelemetry Authors
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

from opentelemetry.sdk import metrics
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricsExporter,
    MetricRecord,
)
from opentelemetry.sdk.metrics.export.aggregate import (
    CounterAggregator,
    MinMaxSumCountAggregator,
)
from opentelemetry.sdk.metrics.export.batcher import UngroupedBatcher
from opentelemetry.sdk.metrics.export.controller import PushController


# pylint: disable=protected-access
class TestConsoleMetricsExporter(unittest.TestCase):
    # pylint: disable=no-self-use
    def test_export(self):
        meter = metrics.Meter()
        exporter = ConsoleMetricsExporter()
        metric = metrics.Counter(
            "available memory",
            "available memory",
            "bytes",
            int,
            meter,
            ("environment",),
        )
        kvp = {"environment": "staging"}
        label_set = meter.get_label_set(kvp)
        aggregator = CounterAggregator()
        record = MetricRecord(aggregator, label_set, metric)
        result = '{}(data="{}", label_set="{}", value={})'.format(
            ConsoleMetricsExporter.__name__,
            metric,
            label_set.labels,
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

    # TODO: Add other aggregator tests

    def test_checkpoint_set(self):
        meter = metrics.Meter()
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
        label_set = metrics.LabelSet()
        _batch_map = {}
        _batch_map[(metric, label_set)] = aggregator
        batcher._batch_map = _batch_map
        records = batcher.checkpoint_set()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].metric, metric)
        self.assertEqual(records[0].label_set, label_set)
        self.assertEqual(records[0].aggregator, aggregator)

    def test_checkpoint_set_empty(self):
        batcher = UngroupedBatcher(True)
        records = batcher.checkpoint_set()
        self.assertEqual(len(records), 0)

    def test_finished_collection_stateless(self):
        meter = metrics.Meter()
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
        label_set = metrics.LabelSet()
        _batch_map = {}
        _batch_map[(metric, label_set)] = aggregator
        batcher._batch_map = _batch_map
        batcher.finished_collection()
        self.assertEqual(len(batcher._batch_map), 0)

    def test_finished_collection_stateful(self):
        meter = metrics.Meter()
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
        label_set = metrics.LabelSet()
        _batch_map = {}
        _batch_map[(metric, label_set)] = aggregator
        batcher._batch_map = _batch_map
        batcher.finished_collection()
        self.assertEqual(len(batcher._batch_map), 1)

    # TODO: Abstract the logic once other batchers implemented
    def test_ungrouped_batcher_process_exists(self):
        meter = metrics.Meter()
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
        label_set = metrics.LabelSet()
        _batch_map = {}
        _batch_map[(metric, label_set)] = aggregator
        aggregator2.update(1.0)
        batcher._batch_map = _batch_map
        record = metrics.Record(metric, label_set, aggregator2)
        batcher.process(record)
        self.assertEqual(len(batcher._batch_map), 1)
        self.assertIsNotNone(batcher._batch_map.get((metric, label_set)))
        self.assertEqual(
            batcher._batch_map.get((metric, label_set)).current, 0
        )
        self.assertEqual(
            batcher._batch_map.get((metric, label_set)).checkpoint, 1.0
        )

    def test_ungrouped_batcher_process_not_exists(self):
        meter = metrics.Meter()
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
        label_set = metrics.LabelSet()
        _batch_map = {}
        aggregator.update(1.0)
        batcher._batch_map = _batch_map
        record = metrics.Record(metric, label_set, aggregator)
        batcher.process(record)
        self.assertEqual(len(batcher._batch_map), 1)
        self.assertIsNotNone(batcher._batch_map.get((metric, label_set)))
        self.assertEqual(
            batcher._batch_map.get((metric, label_set)).current, 0
        )
        self.assertEqual(
            batcher._batch_map.get((metric, label_set)).checkpoint, 1.0
        )

    def test_ungrouped_batcher_process_not_stateful(self):
        meter = metrics.Meter()
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
        label_set = metrics.LabelSet()
        _batch_map = {}
        aggregator.update(1.0)
        batcher._batch_map = _batch_map
        record = metrics.Record(metric, label_set, aggregator)
        batcher.process(record)
        self.assertEqual(len(batcher._batch_map), 1)
        self.assertIsNotNone(batcher._batch_map.get((metric, label_set)))
        self.assertEqual(
            batcher._batch_map.get((metric, label_set)).current, 0
        )
        self.assertEqual(
            batcher._batch_map.get((metric, label_set)).checkpoint, 1.0
        )


class TestCounterAggregator(unittest.TestCase):
    @classmethod
    def call_update(cls, counter):
        update_total = 0
        for _ in range(0, 100000):
            val = random.getrandbits(32)
            counter.update(val)
            update_total += val
        return update_total

    def test_update(self):
        counter = CounterAggregator()
        counter.update(1.0)
        counter.update(2.0)
        self.assertEqual(counter.current, 3.0)

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
        counter.merge(counter2)
        self.assertEqual(counter.checkpoint, 4.0)

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

            while fut.running():
                counter.take_checkpoint()
                checkpoint_total += counter.checkpoint

        counter.take_checkpoint()
        checkpoint_total += counter.checkpoint

        self.assertEqual(fut.result(), checkpoint_total)


class TestMinMaxSumCountAggregator(unittest.TestCase):
    @classmethod
    def call_update(cls, mmsc):
        min_ = 2 ** 32
        max_ = 0
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

    def test_update(self):
        mmsc = MinMaxSumCountAggregator()
        # test current values without any update
        self.assertEqual(
            mmsc.current, MinMaxSumCountAggregator._EMPTY,
        )

        # call update with some values
        values = (3, 50, 3, 97)
        for val in values:
            mmsc.update(val)

        self.assertEqual(
            mmsc.current, (min(values), max(values), sum(values), len(values)),
        )

    def test_checkpoint(self):
        mmsc = MinMaxSumCountAggregator()

        # take checkpoint wihtout any update
        mmsc.take_checkpoint()
        self.assertEqual(
            mmsc.checkpoint, MinMaxSumCountAggregator._EMPTY,
        )

        # call update with some values
        values = (3, 50, 3, 97)
        for val in values:
            mmsc.update(val)

        mmsc.take_checkpoint()
        self.assertEqual(
            mmsc.checkpoint,
            (min(values), max(values), sum(values), len(values)),
        )

        self.assertEqual(
            mmsc.current, MinMaxSumCountAggregator._EMPTY,
        )

    def test_merge(self):
        mmsc1 = MinMaxSumCountAggregator()
        mmsc2 = MinMaxSumCountAggregator()

        checkpoint1 = MinMaxSumCountAggregator._TYPE(3, 150, 101, 3)
        checkpoint2 = MinMaxSumCountAggregator._TYPE(1, 33, 44, 2)

        mmsc1.checkpoint = checkpoint1
        mmsc2.checkpoint = checkpoint2

        mmsc1.merge(mmsc2)

        self.assertEqual(
            mmsc1.checkpoint,
            MinMaxSumCountAggregator._merge_checkpoint(
                checkpoint1, checkpoint2
            ),
        )

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

            while fut.running():
                mmsc.take_checkpoint()
                checkpoint_total = MinMaxSumCountAggregator._merge_checkpoint(
                    checkpoint_total, mmsc.checkpoint
                )

            mmsc.take_checkpoint()
            checkpoint_total = MinMaxSumCountAggregator._merge_checkpoint(
                checkpoint_total, mmsc.checkpoint
            )

            self.assertEqual(checkpoint_total, fut.result())


class TestController(unittest.TestCase):
    def test_push_controller(self):
        meter = mock.Mock()
        exporter = mock.Mock()
        controller = PushController(meter, exporter, 5.0)
        meter.collect.assert_not_called()
        exporter.export.assert_not_called()
        controller.shutdown()
        self.assertTrue(controller.finished.isSet())
        exporter.shutdown.assert_any_call()
