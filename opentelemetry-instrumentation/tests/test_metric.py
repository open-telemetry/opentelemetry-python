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
# type: ignore

import time

from unittest import mock, TestCase

from opentelemetry import metrics as metrics_api
from opentelemetry.trace import SpanKind
from opentelemetry.instrumentation.metric import (
    MetricMixin,
    HTTPMetricRecorder,
)
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk import metrics
from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter


class TestMetricMixin(TestCase):
    @classmethod
    def setUpClass(cls):
        metrics_api._METER_PROVIDER = None
        set_meter_provider(metrics.MeterProvider())

    @classmethod
    def tearDownClass(cls):
        metrics_api._METER_PROVIDER = None

    def test_init(self):
        mixin = MetricMixin()
        mixin.init_metrics("test", 1.0)
        meter = mixin.meter
        self.assertTrue(isinstance(meter, metrics.Meter))
        self.assertEqual(meter.instrumentation_info.name, "test")
        self.assertEqual(meter.instrumentation_info.version, 1.0)

    def test_init_exporter(self):
        mixin = MetricMixin()
        exporter = ConsoleMetricsExporter()
        mixin.init_metrics("test", 1.0, exporter, 100.0)
        meter = mixin.meter
        self.assertTrue(isinstance(meter, metrics.Meter))
        self.assertEqual(meter.instrumentation_info.name, "test")
        self.assertEqual(meter.instrumentation_info.version, 1.0)
        # pylint: disable=protected-access
        self.assertEqual(mixin._controller.exporter, exporter)
        self.assertEqual(mixin._controller.meter, meter)
        mixin._controller.shutdown()


class TestHTTPMetricRecorder(TestCase):
    @classmethod
    def setUpClass(cls):
        metrics_api._METER_PROVIDER = None
        set_meter_provider(metrics.MeterProvider())

    @classmethod
    def tearDownClass(cls):
        metrics_api._METER_PROVIDER = None

    def test_ctor(self):
        meter = metrics_api.get_meter(__name__)
        recorder = HTTPMetricRecorder(meter, SpanKind.CLIENT)
        self.assertEqual(recorder.kind, SpanKind.CLIENT)
        # pylint: disable=protected-access
        self.assertTrue(isinstance(recorder._duration, metrics.ValueRecorder))
        self.assertEqual(recorder._duration.name, "http.client.duration")
        self.assertEqual(
            recorder._duration.description,
            "measures the duration of the outbound HTTP request",
        )

    def test_record_duration(self):
        meter = metrics_api.get_meter(__name__)
        recorder = HTTPMetricRecorder(meter, SpanKind.CLIENT)
        labels = {"test": "asd"}
        with recorder.record_duration(labels):
            labels["test2"] = "asd2"
            time.sleep(1)
        match_key = tuple({"test": "asd", "test2": "asd2"}.items())
        for key in recorder._duration.bound_instruments.keys():
            self.assertEqual(key, match_key)
            # pylint: disable=protected-access
            bound = recorder._duration.bound_instruments.get(key)
            for view_data in bound.view_datas:
                self.assertEqual(view_data.labels, key)
                self.assertEqual(view_data.aggregator.current.count, 1)
                self.assertGreater(view_data.aggregator.current.sum, 0)
