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

from os import environ
from typing import Dict, Iterable
from unittest import TestCase
from unittest.mock import patch

from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
)
from opentelemetry.sdk.metrics import (
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
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
        metrics: Iterable[Metric],
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> None:
        pass

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        return True


class TestMetricReader(TestCase):
    @patch.dict(
        environ,
        {OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE: "CUMULATIVE"},
    )
    def test_configure_temporality_cumulative(self):

        dummy_metric_reader = DummyMetricReader()

        self.assertEqual(
            dummy_metric_reader._instrument_class_temporality.keys(),
            set(
                [
                    Counter,
                    UpDownCounter,
                    Histogram,
                    ObservableCounter,
                    ObservableUpDownCounter,
                    ObservableGauge,
                ]
            ),
        )
        for (
            value
        ) in dummy_metric_reader._instrument_class_temporality.values():
            self.assertEqual(value, AggregationTemporality.CUMULATIVE)

    @patch.dict(
        environ, {OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE: "DELTA"}
    )
    def test_configure_temporality_delta(self):

        dummy_metric_reader = DummyMetricReader()

        self.assertEqual(
            dummy_metric_reader._instrument_class_temporality.keys(),
            set(
                [
                    Counter,
                    UpDownCounter,
                    Histogram,
                    ObservableCounter,
                    ObservableUpDownCounter,
                    ObservableGauge,
                ]
            ),
        )
        self.assertEqual(
            dummy_metric_reader._instrument_class_temporality[Counter],
            AggregationTemporality.DELTA,
        )
        self.assertEqual(
            dummy_metric_reader._instrument_class_temporality[UpDownCounter],
            AggregationTemporality.CUMULATIVE,
        )
        self.assertEqual(
            dummy_metric_reader._instrument_class_temporality[Histogram],
            AggregationTemporality.DELTA,
        )
        self.assertEqual(
            dummy_metric_reader._instrument_class_temporality[
                ObservableCounter
            ],
            AggregationTemporality.DELTA,
        )
        self.assertEqual(
            dummy_metric_reader._instrument_class_temporality[
                ObservableUpDownCounter
            ],
            AggregationTemporality.CUMULATIVE,
        )
        self.assertEqual(
            dummy_metric_reader._instrument_class_temporality[ObservableGauge],
            AggregationTemporality.CUMULATIVE,
        )

    def test_configure_temporality_parameter(self):

        dummy_metric_reader = DummyMetricReader(
            preferred_temporality={
                Histogram: AggregationTemporality.DELTA,
                ObservableGauge: AggregationTemporality.DELTA,
            }
        )

        self.assertEqual(
            dummy_metric_reader._instrument_class_temporality.keys(),
            set(
                [
                    Counter,
                    UpDownCounter,
                    Histogram,
                    ObservableCounter,
                    ObservableUpDownCounter,
                    ObservableGauge,
                ]
            ),
        )
        self.assertEqual(
            dummy_metric_reader._instrument_class_temporality[Counter],
            AggregationTemporality.CUMULATIVE,
        )
        self.assertEqual(
            dummy_metric_reader._instrument_class_temporality[UpDownCounter],
            AggregationTemporality.CUMULATIVE,
        )
        self.assertEqual(
            dummy_metric_reader._instrument_class_temporality[Histogram],
            AggregationTemporality.DELTA,
        )
        self.assertEqual(
            dummy_metric_reader._instrument_class_temporality[
                ObservableCounter
            ],
            AggregationTemporality.CUMULATIVE,
        )
        self.assertEqual(
            dummy_metric_reader._instrument_class_temporality[
                ObservableUpDownCounter
            ],
            AggregationTemporality.CUMULATIVE,
        )
        self.assertEqual(
            dummy_metric_reader._instrument_class_temporality[ObservableGauge],
            AggregationTemporality.DELTA,
        )

    def test_default_temporality(self):
        dummy_metric_reader = DummyMetricReader()
        self.assertEqual(
            dummy_metric_reader._instrument_class_aggregation.keys(),
            set(
                [
                    Counter,
                    UpDownCounter,
                    Histogram,
                    ObservableCounter,
                    ObservableUpDownCounter,
                    ObservableGauge,
                ]
            ),
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
            set(
                [
                    Counter,
                    UpDownCounter,
                    Histogram,
                    ObservableCounter,
                    ObservableUpDownCounter,
                    ObservableGauge,
                ]
            ),
        )
        self.assertIsInstance(
            dummy_metric_reader._instrument_class_aggregation[Counter],
            LastValueAggregation,
        )
