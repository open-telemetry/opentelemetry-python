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

from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    Buckets,
    ExponentialHistogram,
    ExponentialHistogramDataPoint,
    Gauge,
    Histogram,
    HistogramDataPoint,
    Metric,
    MetricsData,
    NumberDataPoint,
    ResourceMetrics,
    ScopeMetrics,
    Sum,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope


class TestToJson(TestCase):
    @classmethod
    def setUpClass(cls):

        cls.attributes_0 = {
            "a": "b",
            "b": True,
            "c": 1,
            "d": 1.1,
            "e": ["a", "b"],
            "f": [True, False],
            "g": [1, 2],
            "h": [1.1, 2.2],
        }
        cls.attributes_0_str = '{"a": "b", "b": true, "c": 1, "d": 1.1, "e": ["a", "b"], "f": [true, false], "g": [1, 2], "h": [1.1, 2.2]}'

        cls.attributes_1 = {
            "i": "a",
            "j": False,
            "k": 2,
            "l": 2.2,
            "m": ["b", "a"],
            "n": [False, True],
            "o": [2, 1],
            "p": [2.2, 1.1],
        }
        cls.attributes_1_str = '{"i": "a", "j": false, "k": 2, "l": 2.2, "m": ["b", "a"], "n": [false, true], "o": [2, 1], "p": [2.2, 1.1]}'

        cls.number_data_point_0 = NumberDataPoint(
            attributes=cls.attributes_0,
            start_time_unix_nano=1,
            time_unix_nano=2,
            value=3.3,
        )
        cls.number_data_point_0_str = f'{{"attributes": {cls.attributes_0_str}, "start_time_unix_nano": 1, "time_unix_nano": 2, "value": 3.3}}'

        cls.number_data_point_1 = NumberDataPoint(
            attributes=cls.attributes_1,
            start_time_unix_nano=2,
            time_unix_nano=3,
            value=4.4,
        )
        cls.number_data_point_1_str = f'{{"attributes": {cls.attributes_1_str}, "start_time_unix_nano": 2, "time_unix_nano": 3, "value": 4.4}}'

        cls.histogram_data_point_0 = HistogramDataPoint(
            attributes=cls.attributes_0,
            start_time_unix_nano=1,
            time_unix_nano=2,
            count=3,
            sum=3.3,
            bucket_counts=[1, 1, 1],
            explicit_bounds=[0.1, 1.2, 2.3, 3.4],
            min=0.2,
            max=3.3,
        )
        cls.histogram_data_point_0_str = f'{{"attributes": {cls.attributes_0_str}, "start_time_unix_nano": 1, "time_unix_nano": 2, "count": 3, "sum": 3.3, "bucket_counts": [1, 1, 1], "explicit_bounds": [0.1, 1.2, 2.3, 3.4], "min": 0.2, "max": 3.3}}'

        cls.histogram_data_point_1 = HistogramDataPoint(
            attributes=cls.attributes_1,
            start_time_unix_nano=2,
            time_unix_nano=3,
            count=4,
            sum=4.4,
            bucket_counts=[2, 1, 1],
            explicit_bounds=[1.2, 2.3, 3.4, 4.5],
            min=0.3,
            max=4.4,
        )
        cls.histogram_data_point_1_str = f'{{"attributes": {cls.attributes_1_str}, "start_time_unix_nano": 2, "time_unix_nano": 3, "count": 4, "sum": 4.4, "bucket_counts": [2, 1, 1], "explicit_bounds": [1.2, 2.3, 3.4, 4.5], "min": 0.3, "max": 4.4}}'

        cls.exp_histogram_data_point_0 = ExponentialHistogramDataPoint(
            attributes=cls.attributes_0,
            start_time_unix_nano=1,
            time_unix_nano=2,
            count=1,
            sum=10,
            scale=1,
            zero_count=0,
            positive=Buckets(offset=0, bucket_counts=[1]),
            negative=Buckets(offset=0, bucket_counts=[0]),
            flags=0,
            min=10,
            max=10,
        )
        cls.exp_histogram_data_point_0_str = f'{{"attributes": {cls.attributes_0_str}, "start_time_unix_nano": 1, "time_unix_nano": 2, "count": 1, "sum": 10, "scale": 1, "zero_count": 0, "positive": {{"offset": 0, "bucket_counts": [1]}}, "negative": {{"offset": 0, "bucket_counts": [0]}}, "flags": 0, "min": 10, "max": 10}}'

        cls.sum_0 = Sum(
            data_points=[cls.number_data_point_0, cls.number_data_point_1],
            aggregation_temporality=AggregationTemporality.DELTA,
            is_monotonic=False,
        )
        cls.sum_0_str = f'{{"data_points": [{cls.number_data_point_0_str}, {cls.number_data_point_1_str}], "aggregation_temporality": 1, "is_monotonic": false}}'

        cls.gauge_0 = Gauge(
            data_points=[cls.number_data_point_0, cls.number_data_point_1],
        )
        cls.gauge_0_str = f'{{"data_points": [{cls.number_data_point_0_str}, {cls.number_data_point_1_str}]}}'

        cls.histogram_0 = Histogram(
            data_points=[
                cls.histogram_data_point_0,
                cls.histogram_data_point_1,
            ],
            aggregation_temporality=AggregationTemporality.DELTA,
        )
        cls.histogram_0_str = f'{{"data_points": [{cls.histogram_data_point_0_str}, {cls.histogram_data_point_1_str}], "aggregation_temporality": 1}}'

        cls.exp_histogram_0 = ExponentialHistogram(
            data_points=[
                cls.exp_histogram_data_point_0,
            ],
            aggregation_temporality=AggregationTemporality.CUMULATIVE,
        )
        cls.exp_histogram_0_str = f'{{"data_points": [{cls.exp_histogram_data_point_0_str}], "aggregation_temporality": 2}}'

        cls.metric_0 = Metric(
            name="metric_0",
            description="description_0",
            unit="unit_0",
            data=cls.sum_0,
        )
        cls.metric_0_str = f'{{"name": "metric_0", "description": "description_0", "unit": "unit_0", "data": {cls.sum_0_str}}}'

        cls.metric_1 = Metric(
            name="metric_1", description=None, unit="unit_1", data=cls.gauge_0
        )
        cls.metric_1_str = f'{{"name": "metric_1", "description": "", "unit": "unit_1", "data": {cls.gauge_0_str}}}'

        cls.metric_2 = Metric(
            name="metric_2",
            description="description_2",
            unit=None,
            data=cls.histogram_0,
        )
        cls.metric_2_str = f'{{"name": "metric_2", "description": "description_2", "unit": "", "data": {cls.histogram_0_str}}}'

        cls.scope_metrics_0 = ScopeMetrics(
            scope=InstrumentationScope(
                name="name_0",
                version="version_0",
                schema_url="schema_url_0",
            ),
            metrics=[cls.metric_0, cls.metric_1, cls.metric_2],
            schema_url="schema_url_0",
        )
        cls.scope_metrics_0_str = f'{{"scope": {{"name": "name_0", "version": "version_0", "schema_url": "schema_url_0", "attributes": null}}, "metrics": [{cls.metric_0_str}, {cls.metric_1_str}, {cls.metric_2_str}], "schema_url": "schema_url_0"}}'

        cls.scope_metrics_1 = ScopeMetrics(
            scope=InstrumentationScope(
                name="name_1",
                version="version_1",
                schema_url="schema_url_1",
            ),
            metrics=[cls.metric_0, cls.metric_1, cls.metric_2],
            schema_url="schema_url_1",
        )
        cls.scope_metrics_1_str = f'{{"scope": {{"name": "name_1", "version": "version_1", "schema_url": "schema_url_1", "attributes": null}}, "metrics": [{cls.metric_0_str}, {cls.metric_1_str}, {cls.metric_2_str}], "schema_url": "schema_url_1"}}'

        cls.resource_metrics_0 = ResourceMetrics(
            resource=Resource(
                attributes=cls.attributes_0, schema_url="schema_url_0"
            ),
            scope_metrics=[cls.scope_metrics_0, cls.scope_metrics_1],
            schema_url="schema_url_0",
        )
        cls.resource_metrics_0_str = f'{{"resource": {{"attributes": {cls.attributes_0_str}, "schema_url": "schema_url_0"}}, "scope_metrics": [{cls.scope_metrics_0_str}, {cls.scope_metrics_1_str}], "schema_url": "schema_url_0"}}'

        cls.resource_metrics_1 = ResourceMetrics(
            resource=Resource(
                attributes=cls.attributes_1, schema_url="schema_url_1"
            ),
            scope_metrics=[cls.scope_metrics_0, cls.scope_metrics_1],
            schema_url="schema_url_1",
        )
        cls.resource_metrics_1_str = f'{{"resource": {{"attributes": {cls.attributes_1_str}, "schema_url": "schema_url_1"}}, "scope_metrics": [{cls.scope_metrics_0_str}, {cls.scope_metrics_1_str}], "schema_url": "schema_url_1"}}'

        cls.metrics_data_0 = MetricsData(
            resource_metrics=[cls.resource_metrics_0, cls.resource_metrics_1]
        )
        cls.metrics_data_0_str = f'{{"resource_metrics": [{cls.resource_metrics_0_str}, {cls.resource_metrics_1_str}]}}'

    def test_number_data_point(self):

        self.assertEqual(
            self.number_data_point_0.to_json(indent=None),
            self.number_data_point_0_str,
        )
        self.assertEqual(
            self.number_data_point_1.to_json(indent=None),
            self.number_data_point_1_str,
        )

    def test_histogram_data_point(self):

        self.assertEqual(
            self.histogram_data_point_0.to_json(indent=None),
            self.histogram_data_point_0_str,
        )
        self.assertEqual(
            self.histogram_data_point_1.to_json(indent=None),
            self.histogram_data_point_1_str,
        )

    def test_exp_histogram_data_point(self):

        self.assertEqual(
            self.exp_histogram_data_point_0.to_json(indent=None),
            self.exp_histogram_data_point_0_str,
        )

    def test_sum(self):

        self.assertEqual(self.sum_0.to_json(indent=None), self.sum_0_str)

    def test_gauge(self):

        self.assertEqual(self.gauge_0.to_json(indent=None), self.gauge_0_str)

    def test_histogram(self):

        self.assertEqual(
            self.histogram_0.to_json(indent=None), self.histogram_0_str
        )

    def test_exp_histogram(self):

        self.assertEqual(
            self.exp_histogram_0.to_json(indent=None), self.exp_histogram_0_str
        )

    def test_metric(self):

        self.assertEqual(self.metric_0.to_json(indent=None), self.metric_0_str)

        self.assertEqual(self.metric_1.to_json(indent=None), self.metric_1_str)

        self.assertEqual(self.metric_2.to_json(indent=None), self.metric_2_str)

    def test_scope_metrics(self):

        self.assertEqual(
            self.scope_metrics_0.to_json(indent=None), self.scope_metrics_0_str
        )
        self.assertEqual(
            self.scope_metrics_1.to_json(indent=None), self.scope_metrics_1_str
        )

    def test_resource_metrics(self):

        self.assertEqual(
            self.resource_metrics_0.to_json(indent=None),
            self.resource_metrics_0_str,
        )
        self.assertEqual(
            self.resource_metrics_1.to_json(indent=None),
            self.resource_metrics_1_str,
        )

    def test_metrics_data(self):

        self.assertEqual(
            self.metrics_data_0.to_json(indent=None), self.metrics_data_0_str
        )
