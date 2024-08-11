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

from typing import Dict, Iterable
from unittest import TestCase
from unittest.mock import patch

from opentelemetry.sdk.metrics import Counter, Histogram, ObservableGauge
from opentelemetry.sdk.metrics import _Gauge as _SDKGauge
from opentelemetry.sdk.metrics._internal.instrument import (
    _Counter,
    _Gauge,
    _Histogram,
    _ObservableCounter,
    _ObservableGauge,
    _ObservableUpDownCounter,
    _UpDownCounter,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    Metric,
    MetricReader,
)
from opentelemetry.sdk.metrics.view import (
    Aggregation,
    DefaultAggregation,
    LastValueAggregation,
)

_expected_keys = [
    _Counter,
    _UpDownCounter,
    _Gauge,
    _Histogram,
    _ObservableCounter,
    _ObservableUpDownCounter,
    _ObservableGauge,
]


class DummyMetricReader(MetricReader):
    def __init__(
        self,
        preferred_temporality: Dict[type, AggregationTemporality] = None,
        preferred_aggregation: Dict[type, Aggregation] = None,
    ) -> None:
        super().__init__(
            preferred_temporality=preferred_temporality,
            preferred_aggregation=preferred_aggregation,
        )

    def _receive_metrics(
        self,
        metrics_data: Iterable[Metric],
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> None:
        pass

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        return True


class TestMetricReader(TestCase):
    def test_configure_temporality(self):

        dummy_metric_reader = DummyMetricReader(
            preferred_temporality={
                Histogram: AggregationTemporality.DELTA,
                ObservableGauge: AggregationTemporality.DELTA,
                _SDKGauge: AggregationTemporality.DELTA,
            }
        )

        self.assertEqual(
            dummy_metric_reader._instrument_class_temporality.keys(),
            set(_expected_keys),
        )
        self.assertEqual(
            dummy_metric_reader._instrument_class_temporality[_Counter],
            AggregationTemporality.CUMULATIVE,
        )
        self.assertEqual(
            dummy_metric_reader._instrument_class_temporality[_UpDownCounter],
            AggregationTemporality.CUMULATIVE,
        )
        self.assertEqual(
            dummy_metric_reader._instrument_class_temporality[_Histogram],
            AggregationTemporality.DELTA,
        )
        self.assertEqual(
            dummy_metric_reader._instrument_class_temporality[
                _ObservableCounter
            ],
            AggregationTemporality.CUMULATIVE,
        )
        self.assertEqual(
            dummy_metric_reader._instrument_class_temporality[
                _ObservableUpDownCounter
            ],
            AggregationTemporality.CUMULATIVE,
        )
        self.assertEqual(
            dummy_metric_reader._instrument_class_temporality[
                _ObservableGauge
            ],
            AggregationTemporality.DELTA,
        )

        self.assertEqual(
            dummy_metric_reader._instrument_class_temporality[_Gauge],
            AggregationTemporality.DELTA,
        )

    def test_configure_aggregation(self):
        dummy_metric_reader = DummyMetricReader()
        self.assertEqual(
            dummy_metric_reader._instrument_class_aggregation.keys(),
            set(_expected_keys),
        )
        for (
            value
        ) in dummy_metric_reader._instrument_class_aggregation.values():
            self.assertIsInstance(value, DefaultAggregation)

        dummy_metric_reader = DummyMetricReader(
            preferred_aggregation={Counter: LastValueAggregation()}
        )
        self.assertEqual(
            dummy_metric_reader._instrument_class_aggregation.keys(),
            set(_expected_keys),
        )
        self.assertIsInstance(
            dummy_metric_reader._instrument_class_aggregation[_Counter],
            LastValueAggregation,
        )

    # pylint: disable=no-self-use
    def test_force_flush(self):

        with patch.object(DummyMetricReader, "collect") as mock_collect:
            DummyMetricReader().force_flush(timeout_millis=10)
            mock_collect.assert_called_with(timeout_millis=10)
