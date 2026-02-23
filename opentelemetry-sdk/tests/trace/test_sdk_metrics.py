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

from unittest import TestCase

from opentelemetry import trace as trace_api
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.sampling import (
    ALWAYS_OFF,
    ALWAYS_ON,
    Decision,
    StaticSampler,
)
from opentelemetry.trace.span import SpanContext


class TestTracerProviderMetrics(TestCase):
    def setUp(self):
        self.metric_reader = InMemoryMetricReader()
        self.meter_provider = MeterProvider(
            metric_readers=[self.metric_reader]
        )

    def tearDown(self):
        self.meter_provider.shutdown()

    def assert_started_spans(self, metric_data, value, attrs):
        metrics = metric_data.resource_metrics[0].scope_metrics[0].metrics
        started_spans_metric = next(
            (m for m in metrics if m.name == "otel.sdk.span.started"), None
        )
        self.assertIsNotNone(started_spans_metric)
        self.assertEqual(started_spans_metric.data.data_points[0].value, value)
        self.assertDictEqual(
            started_spans_metric.data.data_points[0].attributes, attrs
        )

    def assert_live_spans(self, metric_data, value, attrs):
        metrics = metric_data.resource_metrics[0].scope_metrics[0].metrics
        live_spans_metric = next(
            (m for m in metrics if m.name == "otel.sdk.span.live"), None
        )
        if value is None:
            self.assertIsNone(live_spans_metric)
            return
        self.assertIsNotNone(live_spans_metric)
        self.assertEqual(live_spans_metric.data.data_points[0].value, value)
        self.assertDictEqual(
            live_spans_metric.data.data_points[0].attributes, attrs
        )

    def test_sampled(self):
        tracer_provider = TracerProvider(
            sampler=ALWAYS_ON, meter_provider=self.meter_provider
        )
        tracer = tracer_provider.get_tracer("test")
        span = tracer.start_span("span")
        metric_data = self.metric_reader.get_metrics_data()
        self.assert_started_spans(
            metric_data,
            1,
            {
                "otel.span.parent.origin": "none",
                "otel.span.sampling_result": "RECORD_AND_SAMPLE",
            },
        )
        self.assert_live_spans(
            metric_data,
            1,
            {
                "otel.span.sampling_result": "RECORD_AND_SAMPLE",
            },
        )
        span.end()
        metric_data = self.metric_reader.get_metrics_data()
        self.assert_started_spans(
            metric_data,
            1,
            {
                "otel.span.parent.origin": "none",
                "otel.span.sampling_result": "RECORD_AND_SAMPLE",
            },
        )
        self.assert_live_spans(
            metric_data,
            0,
            {
                "otel.span.sampling_result": "RECORD_AND_SAMPLE",
            },
        )

    def test_record_only(self):
        tracer_provider = TracerProvider(
            sampler=StaticSampler(Decision.RECORD_ONLY),
            meter_provider=self.meter_provider,
        )
        tracer = tracer_provider.get_tracer("test")
        span = tracer.start_span("span")
        metric_data = self.metric_reader.get_metrics_data()
        self.assert_started_spans(
            metric_data,
            1,
            {
                "otel.span.parent.origin": "none",
                "otel.span.sampling_result": "RECORD_ONLY",
            },
        )
        self.assert_live_spans(
            metric_data,
            1,
            {
                "otel.span.sampling_result": "RECORD_ONLY",
            },
        )
        span.end()
        metric_data = self.metric_reader.get_metrics_data()
        self.assert_started_spans(
            metric_data,
            1,
            {
                "otel.span.parent.origin": "none",
                "otel.span.sampling_result": "RECORD_ONLY",
            },
        )
        self.assert_live_spans(
            metric_data,
            0,
            {
                "otel.span.sampling_result": "RECORD_ONLY",
            },
        )

    def test_dropped(self):
        tracer_provider = TracerProvider(
            sampler=ALWAYS_OFF, meter_provider=self.meter_provider
        )
        tracer = tracer_provider.get_tracer("test")
        span = tracer.start_span("span")
        metric_data = self.metric_reader.get_metrics_data()
        self.assert_started_spans(
            metric_data,
            1,
            {
                "otel.span.parent.origin": "none",
                "otel.span.sampling_result": "DROP",
            },
        )
        self.assert_live_spans(metric_data, None, {})
        span.end()
        metric_data = self.metric_reader.get_metrics_data()
        self.assert_started_spans(
            metric_data,
            1,
            {
                "otel.span.parent.origin": "none",
                "otel.span.sampling_result": "DROP",
            },
        )
        self.assert_live_spans(metric_data, None, {})

    def test_dropped_remote_parent(self):
        tracer_provider = TracerProvider(
            sampler=ALWAYS_OFF, meter_provider=self.meter_provider
        )
        tracer = tracer_provider.get_tracer("test")
        parent_span_context = SpanContext(
            trace_id=1,
            span_id=2,
            is_remote=True,
        )
        parent_context = trace_api.set_span_in_context(
            trace_api.NonRecordingSpan(parent_span_context)
        )
        span = tracer.start_span("span", context=parent_context)
        metric_data = self.metric_reader.get_metrics_data()
        self.assert_started_spans(
            metric_data,
            1,
            {
                "otel.span.parent.origin": "remote",
                "otel.span.sampling_result": "DROP",
            },
        )
        self.assert_live_spans(metric_data, None, {})
        span.end()
        metric_data = self.metric_reader.get_metrics_data()
        self.assert_started_spans(
            metric_data,
            1,
            {
                "otel.span.parent.origin": "remote",
                "otel.span.sampling_result": "DROP",
            },
        )
        self.assert_live_spans(metric_data, None, {})

    def test_dropped_local_parent(self):
        tracer_provider = TracerProvider(
            sampler=ALWAYS_OFF, meter_provider=self.meter_provider
        )
        tracer = tracer_provider.get_tracer("test")
        parent_span_context = SpanContext(
            trace_id=1,
            span_id=2,
            is_remote=False,
        )
        parent_context = trace_api.set_span_in_context(
            trace_api.NonRecordingSpan(parent_span_context)
        )
        span = tracer.start_span("span", context=parent_context)
        metric_data = self.metric_reader.get_metrics_data()
        self.assert_started_spans(
            metric_data,
            1,
            {
                "otel.span.parent.origin": "local",
                "otel.span.sampling_result": "DROP",
            },
        )
        self.assert_live_spans(metric_data, None, {})
        span.end()
        metric_data = self.metric_reader.get_metrics_data()
        self.assert_started_spans(
            metric_data,
            1,
            {
                "otel.span.parent.origin": "local",
                "otel.span.sampling_result": "DROP",
            },
        )
        self.assert_live_spans(metric_data, None, {})
