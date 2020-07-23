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
from time import time
from unittest.mock import patch

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider, ValueRecorder
from opentelemetry.sdk.metrics.export.aggregate import (
    HistogramAggregator,
    MinMaxExemplarSampler,
    MinMaxSumCountAggregator,
    SumAggregator,
    ValueObserverAggregator,
)
from opentelemetry.sdk.metrics.export.controller import PushController
from opentelemetry.sdk.metrics.export.exemplars import (
    BucketedExemplarSampler,
    Exemplar,
    ExemplarManager,
    RandomExemplarSampler,
)
from opentelemetry.sdk.metrics.export.in_memory_metrics_exporter import (
    InMemoryMetricsExporter,
)
from opentelemetry.sdk.metrics.view import View, ViewConfig
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace.sampling import ALWAYS_OFF, ALWAYS_ON


class TestRandomExemplarSampler(unittest.TestCase):
    def test_sample(self):
        sampler = RandomExemplarSampler(2, statistical=True)
        exemplar1 = Exemplar(1, time())
        exemplar2 = Exemplar(2, time())
        exemplar3 = Exemplar(3, time())

        sampler.sample(exemplar1)
        self.assertEqual(len(sampler.sample_set), 1)
        self.assertEqual(sampler.sample_set[0], exemplar1)
        self.assertEqual(exemplar1.sample_count, 1)

        sampler.sample(exemplar2)
        self.assertEqual(len(sampler.sample_set), 2)
        self.assertEqual(sampler.sample_set[1], exemplar2)
        self.assertEqual(exemplar1.sample_count, 1)
        self.assertEqual(exemplar2.sample_count, 1)

        def _patched_randint(minimum, maximum):
            # pylint: disable=unused-argument
            return minimum

        with patch("random.randint", _patched_randint):
            sampler.sample(exemplar3)
            self.assertEqual(len(sampler.sample_set), 2)
            self.assertEqual(sampler.sample_set[0], exemplar3)
            self.assertEqual(exemplar3.sample_count, 1.5)
            self.assertEqual(exemplar2.sample_count, 1.5)

        def _patched_randint(minimum, maximum):
            # pylint: disable=unused-argument
            return 1

        with patch("random.randint", _patched_randint):
            sampler.sample(exemplar1)
            self.assertEqual(len(sampler.sample_set), 2)
            self.assertEqual(sampler.sample_set[1], exemplar1)
            self.assertEqual(exemplar1.sample_count, 2)

    def test_reset(self):
        sampler = RandomExemplarSampler(2)
        exemplar1 = Exemplar(1, time())
        exemplar2 = Exemplar(2, time())

        sampler.sample(exemplar1)
        sampler.sample(exemplar2)

        sampler.reset()
        self.assertEqual(len(sampler.sample_set), 0)

        sampler.sample(exemplar1)
        self.assertEqual(len(sampler.sample_set), 1)

    def test_merge(self):
        set1 = [1, 2, 3]
        set2 = [4, 5, 6]
        sampler = RandomExemplarSampler(6)
        self.assertEqual(set1 + set2, sampler.merge(set1, set2))
        sampler = RandomExemplarSampler(8)
        self.assertEqual(set1 + set2, sampler.merge(set1, set2))
        sampler = RandomExemplarSampler(4)
        self.assertEqual(4, len(sampler.merge(set1, set2)))


class TestMinMaxExemplarSampler(unittest.TestCase):
    def test_sample(self):
        sampler = MinMaxExemplarSampler(2)
        exemplar1 = Exemplar(1, time())
        exemplar2 = Exemplar(2, time())
        exemplar3 = Exemplar(3, time())

        sampler.sample(exemplar1)
        self.assertEqual(len(sampler.sample_set), 1)
        self.assertEqual(sampler.sample_set[0], exemplar1)

        sampler.sample(exemplar2)
        self.assertEqual(len(sampler.sample_set), 2)
        self.assertEqual(sampler.sample_set[0], exemplar1)
        self.assertEqual(sampler.sample_set[1], exemplar2)

        sampler.sample(exemplar3)
        self.assertEqual(len(sampler.sample_set), 2)
        self.assertEqual(sampler.sample_set[0], exemplar1)
        self.assertEqual(sampler.sample_set[1], exemplar3)

    def test_reset(self):
        sampler = MinMaxExemplarSampler(2)
        exemplar1 = Exemplar(1, time())
        exemplar2 = Exemplar(2, time())

        sampler.sample(exemplar1)
        sampler.sample(exemplar2)

        sampler.reset()
        self.assertEqual(len(sampler.sample_set), 0)

        sampler.sample(exemplar1)
        self.assertEqual(len(sampler.sample_set), 1)

    def test_merge(self):
        set1 = [1, 2, 3]
        set2 = [4, 5, 6]
        sampler = MinMaxExemplarSampler(2)
        self.assertEqual([1, 6], sampler.merge(set1, set2))


class TestBucketedExemplarSampler(unittest.TestCase):
    def test_exemplars(self):
        sampler = BucketedExemplarSampler(
            1, boundaries=[2, 4, 7], statistical=True
        )
        sampler.sample(Exemplar(3, time()), bucket_index=1)
        self.assertEqual(len(sampler.sample_set), 1)
        self.assertEqual(sampler.sample_set[0].value, 3)

        sampler.sample(Exemplar(5, time()), bucket_index=2)

        self.assertEqual(len(sampler.sample_set), 2)
        self.assertEqual(sampler.sample_set[1].value, 5)
        self.assertEqual(sampler.sample_set[1].sample_count, 1)

        def _patched_randint(minimum, maximum):
            # pylint: disable=unused-argument
            return 0

        with patch("random.randint", _patched_randint):
            sampler.sample(Exemplar(6, time()), bucket_index=2)

        self.assertEqual(len(sampler.sample_set), 2)
        self.assertEqual(sampler.sample_set[1].value, 6)
        self.assertEqual(sampler.sample_set[1].sample_count, 2)

        sampler.sample(Exemplar(1, time()), bucket_index=0)
        sampler.sample(Exemplar(9, time()), bucket_index=3)

        self.assertEqual(len(sampler.sample_set), 4)
        self.assertEqual(sampler.sample_set[0].sample_count, 1)
        self.assertEqual(sampler.sample_set[1].sample_count, 1)
        self.assertEqual(sampler.sample_set[2].sample_count, 2)
        self.assertEqual(sampler.sample_set[3].sample_count, 1)

    def test_merge(self):
        sampler = BucketedExemplarSampler(1, boundaries=[3, 4, 6])

        self.assertEqual(
            len(sampler.merge([Exemplar(1, time())], [Exemplar(2, time())])), 1
        )

        self.assertEqual(
            len(
                sampler.merge(
                    [Exemplar(1, time()), Exemplar(5, time())],
                    [Exemplar(2, time())],
                )
            ),
            2,
        )


class TestExemplarManager(unittest.TestCase):
    def test_statistical(self):
        config = {"statistical_exemplars": True, "num_exemplars": 1}
        manager = ExemplarManager(
            config, MinMaxExemplarSampler, RandomExemplarSampler
        )
        self.assertIsInstance(manager.exemplar_sampler, RandomExemplarSampler)
        manager.sample(5, {"dropped_label": "value"})
        self.assertEqual(len(manager.exemplar_sampler.sample_set), 1)
        self.assertEqual(manager.exemplar_sampler.sample_set[0].value, 5)
        self.assertEqual(
            manager.exemplar_sampler.sample_set[0].dropped_labels,
            {"dropped_label": "value"},
        )

        checkpoint = manager.take_checkpoint()
        self.assertEqual(len(checkpoint), 1)
        self.assertEqual(checkpoint[0].value, 5)

        self.assertEqual(len(manager.exemplar_sampler.sample_set), 0)

        merged = manager.merge([Exemplar(2, time())], [Exemplar(3, time())])
        self.assertEqual(len(merged), 1)

    def test_semantic(self):
        config = {"statistical_exemplars": True, "num_exemplars": 1}
        manager = ExemplarManager(
            config, MinMaxExemplarSampler, RandomExemplarSampler
        )
        self.assertIsInstance(manager.exemplar_sampler, RandomExemplarSampler)
        manager.sample(5, {})
        self.assertEqual(len(manager.exemplar_sampler.sample_set), 1)
        self.assertEqual(manager.exemplar_sampler.sample_set[0].value, 5)

        checkpoint = manager.take_checkpoint()
        self.assertEqual(len(checkpoint), 1)
        self.assertEqual(checkpoint[0].value, 5)

        self.assertEqual(len(manager.exemplar_sampler.sample_set), 0)

        merged = manager.merge([Exemplar(2, time())], [Exemplar(3, time())])
        self.assertEqual(len(merged), 1)


class TestStandardExemplars(unittest.TestCase):
    def _no_exemplars_test(self, aggregator):
        config = {}
        agg = aggregator(config=config)
        agg.update(3)
        agg.update(5)
        agg.take_checkpoint()
        self.assertEqual(agg.checkpoint_exemplars, [])

        other_agg = aggregator(
            config={"num_exemplars": 2, "statistical_exemplars": True}
        )
        other_agg.update(2)
        other_agg.update(4)
        other_agg.take_checkpoint()
        self.assertEqual(len(other_agg.checkpoint_exemplars), 2)
        agg.merge(other_agg)
        self.assertEqual(agg.checkpoint_exemplars, [])

    def _simple_exemplars_test(self, aggregator):
        config = {"num_exemplars": 2, "statistical_exemplars": True}
        agg = aggregator(config=config)
        agg.update(2, dropped_labels={"dropped_label": "value"})
        agg.take_checkpoint()
        self.assertEqual(len(agg.checkpoint_exemplars), 1)
        self.assertEqual(agg.checkpoint_exemplars[0].value, 2)
        self.assertEqual(
            agg.checkpoint_exemplars[0].dropped_labels,
            {"dropped_label": "value"},
        )

        agg.update(2)
        agg.update(5)
        agg.take_checkpoint()
        self.assertEqual(len(agg.checkpoint_exemplars), 2)
        self.assertEqual(agg.checkpoint_exemplars[1].value, 5)

        agg.update(2)
        agg.update(5)

        def _patched_randint(minimum, maximum):
            # pylint: disable=unused-argument
            return 1

        with patch("random.randint", _patched_randint):
            agg.update(7)

        agg.take_checkpoint()
        self.assertEqual(len(agg.checkpoint_exemplars), 2)
        self.assertEqual(agg.checkpoint_exemplars[0].value, 2)
        self.assertEqual(agg.checkpoint_exemplars[1].value, 7)

    def _record_traces_only_test(self, aggregator):
        config = {"num_exemplars": 2}
        agg = aggregator(config=config)

        agg.update(2)
        agg.take_checkpoint()
        self.assertEqual(len(agg.checkpoint_exemplars), 0)

        # Test with sampler on/off
        tp = TracerProvider(sampler=ALWAYS_ON)
        tracer = tp.get_tracer(__name__)

        span = tracer.start_span("Test Span ON")
        with tracer.use_span(span):
            agg.update(5)
            agg.update(7)
            agg.update(6)

        agg.take_checkpoint()
        self.assertEqual(len(agg.checkpoint_exemplars), 2)

        self.assertEqual(
            agg.checkpoint_exemplars[0].span_id, span.context.span_id
        )
        self.assertEqual(agg.checkpoint_exemplars[0].value, 5)
        self.assertEqual(agg.checkpoint_exemplars[1].value, 7)

        tp = TracerProvider(sampler=ALWAYS_OFF)
        tracer = tp.get_tracer(__name__)

        with tracer.start_as_current_span("Test Span OFF"):
            agg.update(5)

        agg.take_checkpoint()
        self.assertEqual(len(agg.checkpoint_exemplars), 0)

    def _merge_aggregators_test(self, aggregator):
        config = {"num_exemplars": 2, "statistical_exemplars": True}

        agg1 = aggregator(config=config)
        agg2 = aggregator(config=config)

        agg1.update(1)
        agg1.take_checkpoint()

        agg2.update(2)
        agg2.take_checkpoint()

        self.assertEqual(len(agg1.checkpoint_exemplars), 1)
        self.assertEqual(len(agg2.checkpoint_exemplars), 1)

        agg1.merge(agg2)

        self.assertEqual(len(agg1.checkpoint_exemplars), 2)

    def test_sum_aggregator(self):
        self._no_exemplars_test(SumAggregator)
        self._simple_exemplars_test(SumAggregator)
        self._record_traces_only_test(SumAggregator)
        self._merge_aggregators_test(SumAggregator)

    def test_mmsc_aggregator(self):
        self._no_exemplars_test(MinMaxSumCountAggregator)
        self._simple_exemplars_test(MinMaxSumCountAggregator)
        self._record_traces_only_test(MinMaxSumCountAggregator)
        self._merge_aggregators_test(MinMaxSumCountAggregator)

    def test_observer_aggregator(self):
        self._no_exemplars_test(ValueObserverAggregator)
        self._simple_exemplars_test(ValueObserverAggregator)
        self._record_traces_only_test(ValueObserverAggregator)
        self._merge_aggregators_test(ValueObserverAggregator)


class TestHistogramExemplars(unittest.TestCase):
    def test_no_exemplars(self):
        config = {"bounds": [2, 4, 6]}
        agg = HistogramAggregator(config=config)
        agg.update(3)
        agg.update(5)
        agg.take_checkpoint()
        self.assertEqual(agg.checkpoint_exemplars, [])

        other_agg = HistogramAggregator(
            config=dict(
                config, **{"num_exemplars": 1, "statistical_exemplars": True}
            )
        )

        other_agg.update(3)
        other_agg.update(5)
        other_agg.take_checkpoint()
        self.assertEqual(len(other_agg.checkpoint_exemplars), 2)

        agg.merge(other_agg)
        self.assertEqual(agg.checkpoint_exemplars, [])

    def test_simple_exemplars(self):
        config = {
            "bounds": [2, 4, 7],
            "num_exemplars": 1,
            "statistical_exemplars": True,
        }
        agg = HistogramAggregator(config=config)
        agg.update(2, dropped_labels={"dropped_label": "value"})
        agg.take_checkpoint()
        self.assertEqual(len(agg.checkpoint_exemplars), 1)
        self.assertEqual(agg.checkpoint_exemplars[0].value, 2)
        self.assertEqual(
            agg.checkpoint_exemplars[0].dropped_labels,
            {"dropped_label": "value"},
        )

        agg.update(2)
        agg.update(5)
        agg.take_checkpoint()
        self.assertEqual(len(agg.checkpoint_exemplars), 2)
        self.assertEqual(agg.checkpoint_exemplars[1].value, 5)

        agg.update(5)

        def _patched_randint(minimum, maximum):
            # pylint: disable=unused-argument
            return 0

        with patch("random.randint", _patched_randint):
            agg.update(6)

        agg.take_checkpoint()
        self.assertEqual(len(agg.checkpoint_exemplars), 1)
        self.assertEqual(agg.checkpoint_exemplars[0].value, 6)

        agg.update(1)
        agg.update(3)
        agg.update(6)
        agg.update(9)
        agg.take_checkpoint()
        self.assertEqual(len(agg.checkpoint_exemplars), 4)

    def test_record_traces_only(self):
        config = {
            "bounds": [2, 4, 6],
            "num_exemplars": 2,
            "statistical_exemplars": False,
        }
        agg = HistogramAggregator(config=config)

        agg.update(2)
        agg.take_checkpoint()
        self.assertEqual(len(agg.checkpoint_exemplars), 0)

        # Test with sampler on/off
        tp = TracerProvider(sampler=ALWAYS_ON)
        tracer = tp.get_tracer(__name__)

        span = tracer.start_span("Test Span ON")
        with tracer.use_span(span):
            agg.update(5)

        agg.take_checkpoint()
        self.assertEqual(len(agg.checkpoint_exemplars), 1)

        self.assertEqual(
            agg.checkpoint_exemplars[0].span_id, span.context.span_id
        )

        tp = TracerProvider(sampler=ALWAYS_OFF)
        tracer = tp.get_tracer(__name__)

        with tracer.start_as_current_span("Test Span OFF"):
            agg.update(5)

        agg.take_checkpoint()
        self.assertEqual(len(agg.checkpoint_exemplars), 0)


class TestFullPipelineExemplars(unittest.TestCase):
    def test_histogram(self):
        # Use the meter type provided by the SDK package
        metrics.set_meter_provider(MeterProvider())
        meter = metrics.get_meter(__name__)
        exporter = InMemoryMetricsExporter()
        controller = PushController(meter, exporter, 5)

        requests_size = meter.create_metric(
            name="requests_size",
            description="size of requests",
            unit="1",
            value_type=int,
            metric_type=ValueRecorder,
        )

        size_view = View(
            requests_size,
            HistogramAggregator,
            aggregator_config={
                "bounds": (20, 40, 60, 80, 100),
                "num_exemplars": 1,
                "statistical_exemplars": True,
            },
            label_keys=["environment"],
            view_config=ViewConfig.LABEL_KEYS,
        )

        meter.register_view(size_view)

        # Since this is using the HistogramAggregator, the bucket counts will be reflected
        # with each record
        requests_size.record(25, {"environment": "staging", "test": "value"})
        requests_size.record(1, {"environment": "staging", "test": "value2"})
        requests_size.record(200, {"environment": "staging", "test": "value3"})

        controller.tick()
        metrics_list = exporter.get_exported_metrics()
        self.assertEqual(len(metrics_list), 1)
        exemplars = metrics_list[0].aggregator.checkpoint_exemplars
        self.assertEqual(len(exemplars), 3)
        self.assertEqual(
            [
                (exemplar.value, exemplar.dropped_labels)
                for exemplar in exemplars
            ],
            [
                (1, (("test", "value2"),)),
                (25, (("test", "value"),)),
                (200, (("test", "value3"),)),
            ],
        )
