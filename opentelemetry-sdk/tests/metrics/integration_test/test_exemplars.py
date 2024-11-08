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
import os
from unittest import TestCase, mock

from opentelemetry import trace as trace_api
from opentelemetry.sdk.metrics import Exemplar, MeterProvider
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    InMemoryMetricReader,
    Metric,
    NumberDataPoint,
    Sum,
)
from opentelemetry.trace import SpanContext, TraceFlags


class TestExemplars(TestCase):
    TRACE_ID = int("d4cda95b652f4a1592b449d5929fda1b", 16)
    SPAN_ID = int("6e0c63257de34c92", 16)

    @mock.patch.dict(os.environ, {"OTEL_METRICS_EXEMPLAR_FILTER": "always_on"})
    def test_always_on_exemplars(self):
        reader = InMemoryMetricReader()
        meter_provider = MeterProvider(
            metric_readers=[reader],
        )
        meter = meter_provider.get_meter("testmeter")
        counter = meter.create_counter("testcounter")
        counter.add(10, {"label": "value1"})
        data = reader.get_metrics_data()
        metrics = data.resource_metrics[0].scope_metrics[0].metrics
        self.assertEqual(
            metrics,
            [
                Metric(
                    name="testcounter",
                    description="",
                    unit="",
                    data=Sum(
                        data_points=[
                            NumberDataPoint(
                                attributes={"label": "value1"},
                                start_time_unix_nano=mock.ANY,
                                time_unix_nano=mock.ANY,
                                value=10,
                                exemplars=[
                                    Exemplar(
                                        filtered_attributes={},
                                        value=10,
                                        time_unix_nano=mock.ANY,
                                        span_id=None,
                                        trace_id=None,
                                    ),
                                ],
                            )
                        ],
                        aggregation_temporality=AggregationTemporality.CUMULATIVE,
                        is_monotonic=True,
                    ),
                )
            ],
        )

    @mock.patch.dict(
        os.environ, {"OTEL_METRICS_EXEMPLAR_FILTER": "trace_based"}
    )
    def test_trace_based_exemplars(self):
        span_context = SpanContext(
            trace_id=self.TRACE_ID,
            span_id=self.SPAN_ID,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
            trace_state={},
        )
        span = trace_api.NonRecordingSpan(span_context)
        trace_api.set_span_in_context(span)
        reader = InMemoryMetricReader()
        meter_provider = MeterProvider(
            metric_readers=[reader],
        )

        meter = meter_provider.get_meter("testmeter")
        counter = meter.create_counter("testcounter")
        with trace_api.use_span(span):
            counter.add(10, {"label": "value1"})
        data = reader.get_metrics_data()
        metrics = data.resource_metrics[0].scope_metrics[0].metrics
        self.assertEqual(
            metrics,
            [
                Metric(
                    name="testcounter",
                    description="",
                    unit="",
                    data=Sum(
                        data_points=[
                            NumberDataPoint(
                                attributes={"label": "value1"},
                                start_time_unix_nano=mock.ANY,
                                time_unix_nano=mock.ANY,
                                value=10,
                                exemplars=[
                                    Exemplar(
                                        filtered_attributes={},
                                        value=10,
                                        time_unix_nano=mock.ANY,
                                        span_id=self.SPAN_ID,
                                        trace_id=self.TRACE_ID,
                                    ),
                                ],
                            )
                        ],
                        aggregation_temporality=AggregationTemporality.CUMULATIVE,
                        is_monotonic=True,
                    ),
                )
            ],
        )

    def test_default_exemplar_filter_no_span(self):
        reader = InMemoryMetricReader()
        meter_provider = MeterProvider(
            metric_readers=[reader],
        )

        meter = meter_provider.get_meter("testmeter")
        counter = meter.create_counter("testcounter")
        counter.add(10, {"label": "value1"})
        data = reader.get_metrics_data()
        metrics = data.resource_metrics[0].scope_metrics[0].metrics
        self.assertEqual(
            metrics,
            [
                Metric(
                    name="testcounter",
                    description="",
                    unit="",
                    data=Sum(
                        data_points=[
                            NumberDataPoint(
                                attributes={"label": "value1"},
                                start_time_unix_nano=mock.ANY,
                                time_unix_nano=mock.ANY,
                                value=10,
                                exemplars=[],
                            )
                        ],
                        aggregation_temporality=AggregationTemporality.CUMULATIVE,
                        is_monotonic=True,
                    ),
                )
            ],
        )

    def test_default_exemplar_filter(self):
        span_context = SpanContext(
            trace_id=self.TRACE_ID,
            span_id=self.SPAN_ID,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
            trace_state={},
        )
        span = trace_api.NonRecordingSpan(span_context)
        trace_api.set_span_in_context(span)
        reader = InMemoryMetricReader()
        meter_provider = MeterProvider(
            metric_readers=[reader],
        )

        meter = meter_provider.get_meter("testmeter")
        counter = meter.create_counter("testcounter")
        with trace_api.use_span(span):
            counter.add(10, {"label": "value1"})
        data = reader.get_metrics_data()
        metrics = data.resource_metrics[0].scope_metrics[0].metrics
        self.assertEqual(
            metrics,
            [
                Metric(
                    name="testcounter",
                    description="",
                    unit="",
                    data=Sum(
                        data_points=[
                            NumberDataPoint(
                                attributes={"label": "value1"},
                                start_time_unix_nano=mock.ANY,
                                time_unix_nano=mock.ANY,
                                value=10,
                                exemplars=[
                                    Exemplar(
                                        filtered_attributes={},
                                        value=10,
                                        time_unix_nano=mock.ANY,
                                        span_id=self.SPAN_ID,
                                        trace_id=self.TRACE_ID,
                                    ),
                                ],
                            )
                        ],
                        aggregation_temporality=AggregationTemporality.CUMULATIVE,
                        is_monotonic=True,
                    ),
                )
            ],
        )

    def test_exemplar_trace_based_manual_context(self):
        span_context = SpanContext(
            trace_id=self.TRACE_ID,
            span_id=self.SPAN_ID,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
            trace_state={},
        )
        span = trace_api.NonRecordingSpan(span_context)
        ctx = trace_api.set_span_in_context(span)
        reader = InMemoryMetricReader()
        meter_provider = MeterProvider(
            metric_readers=[reader],
        )

        meter = meter_provider.get_meter("testmeter")
        counter = meter.create_counter("testcounter")
        counter.add(10, {"label": "value1"}, context=ctx)
        data = reader.get_metrics_data()
        metrics = data.resource_metrics[0].scope_metrics[0].metrics
        self.assertEqual(
            metrics,
            [
                Metric(
                    name="testcounter",
                    description="",
                    unit="",
                    data=Sum(
                        data_points=[
                            NumberDataPoint(
                                attributes={"label": "value1"},
                                start_time_unix_nano=mock.ANY,
                                time_unix_nano=mock.ANY,
                                value=10,
                                exemplars=[
                                    Exemplar(
                                        filtered_attributes={},
                                        value=10,
                                        time_unix_nano=mock.ANY,
                                        span_id=self.SPAN_ID,
                                        trace_id=self.TRACE_ID,
                                    ),
                                ],
                            )
                        ],
                        aggregation_temporality=AggregationTemporality.CUMULATIVE,
                        is_monotonic=True,
                    ),
                )
            ],
        )

    @mock.patch.dict(
        os.environ, {"OTEL_METRICS_EXEMPLAR_FILTER": "always_off"}
    )
    def test_always_off_exemplars(self):
        span_context = SpanContext(
            trace_id=self.TRACE_ID,
            span_id=self.SPAN_ID,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
            trace_state={},
        )
        span = trace_api.NonRecordingSpan(span_context)
        trace_api.set_span_in_context(span)
        reader = InMemoryMetricReader()
        meter_provider = MeterProvider(
            metric_readers=[reader],
        )
        meter = meter_provider.get_meter("testmeter")
        counter = meter.create_counter("testcounter")
        with trace_api.use_span(span):
            counter.add(10, {"label": "value1"})
        data = reader.get_metrics_data()
        metrics = data.resource_metrics[0].scope_metrics[0].metrics
        self.assertEqual(
            metrics,
            [
                Metric(
                    name="testcounter",
                    description="",
                    unit="",
                    data=Sum(
                        data_points=[
                            NumberDataPoint(
                                attributes={"label": "value1"},
                                start_time_unix_nano=mock.ANY,
                                time_unix_nano=mock.ANY,
                                value=10,
                                exemplars=[],
                            )
                        ],
                        aggregation_temporality=AggregationTemporality.CUMULATIVE,
                        is_monotonic=True,
                    ),
                )
            ],
        )
