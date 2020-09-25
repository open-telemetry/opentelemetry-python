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

from unittest import TestCase, mock

from opentelemetry import metrics as metrics_api
from opentelemetry.instrumentation.metric import (
    HTTPMetricRecorder,
    HTTPMetricType,
    MetricMixin,
)
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk import metrics
from opentelemetry.sdk.util import get_dict_as_key


# pylint: disable=protected-access
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
        recorder = HTTPMetricRecorder(meter, HTTPMetricType.CLIENT)
        # pylint: disable=protected-access
        self.assertEqual(recorder._http_type, HTTPMetricType.CLIENT)
        self.assertTrue(isinstance(recorder._duration, metrics.ValueRecorder))
        self.assertEqual(recorder._duration.name, "http.client.duration")
        self.assertEqual(
            recorder._duration.description,
            "measures the duration of the outbound HTTP request",
        )

    def test_record_duration(self):
        meter = metrics_api.get_meter(__name__)
        recorder = HTTPMetricRecorder(meter, HTTPMetricType.CLIENT)
        labels = {"test": "asd"}
        with mock.patch("time.time") as time_patch:
            time_patch.return_value = 5.0
            with recorder.record_duration(labels):
                labels["test2"] = "asd2"
        match_key = get_dict_as_key({"test": "asd", "test2": "asd2"})
        for key in recorder._duration.bound_instruments.keys():
            self.assertEqual(key, match_key)
            # pylint: disable=protected-access
            bound = recorder._duration.bound_instruments.get(key)
            for view_data in bound.view_datas:
                self.assertEqual(view_data.labels, key)
                self.assertEqual(view_data.aggregator.current.count, 1)
                self.assertGreaterEqual(view_data.aggregator.current.sum, 0)
