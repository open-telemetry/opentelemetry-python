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
    Gauge,
    Histogram,
    HistogramDataPoint,
    Metric,
    NumberDataPoint,
    Sum,
)


def _create_metric(data):
    return Metric(
        name="test-name",
        description="test-description",
        unit="test-unit",
        data=data,
    )


class TestDatapointToJSON(TestCase):
    def test_sum(self):
        self.maxDiff = None
        point = _create_metric(
            Sum(
                data_points=[
                    NumberDataPoint(
                        attributes={"attr-key": "test-val"},
                        start_time_unix_nano=10,
                        time_unix_nano=20,
                        value=9,
                    )
                ],
                aggregation_temporality=2,
                is_monotonic=True,
            )
        )
        self.assertEqual(
            '{"name": "test-name", "description": "test-description", "unit": "test-unit", "data": "{\\"data_points\\": \\"[{\\\\\\"attributes\\\\\\": {\\\\\\"attr-key\\\\\\": \\\\\\"test-val\\\\\\"}, \\\\\\"start_time_unix_nano\\\\\\": 10, \\\\\\"time_unix_nano\\\\\\": 20, \\\\\\"value\\\\\\": 9}]\\", \\"aggregation_temporality\\": 2, \\"is_monotonic\\": true}"}',
            point.to_json(),
        )

    def test_gauge(self):
        point = _create_metric(
            Gauge(
                data_points=[
                    NumberDataPoint(
                        attributes={"attr-key": "test-val"},
                        start_time_unix_nano=10,
                        time_unix_nano=20,
                        value=9,
                    )
                ]
            )
        )
        self.assertEqual(
            '{"name": "test-name", "description": "test-description", "unit": "test-unit", "data": "{\\"data_points\\": \\"[{\\\\\\"attributes\\\\\\": {\\\\\\"attr-key\\\\\\": \\\\\\"test-val\\\\\\"}, \\\\\\"start_time_unix_nano\\\\\\": 10, \\\\\\"time_unix_nano\\\\\\": 20, \\\\\\"value\\\\\\": 9}]\\"}"}',
            point.to_json(),
        )

    def test_histogram(self):
        point = _create_metric(
            Histogram(
                data_points=[
                    HistogramDataPoint(
                        attributes={"attr-key": "test-val"},
                        start_time_unix_nano=50,
                        time_unix_nano=60,
                        count=1,
                        sum=0.8,
                        bucket_counts=[0, 0, 1, 0],
                        explicit_bounds=[0.1, 0.5, 0.9, 1],
                        min=0.8,
                        max=0.8,
                    )
                ],
                aggregation_temporality=1,
            )
        )
        self.maxDiff = None
        self.assertEqual(
            '{"name": "test-name", "description": "test-description", "unit": "test-unit", "data": "{\\"data_points\\": \\"[{\\\\\\"attributes\\\\\\": {\\\\\\"attr-key\\\\\\": \\\\\\"test-val\\\\\\"}, \\\\\\"start_time_unix_nano\\\\\\": 50, \\\\\\"time_unix_nano\\\\\\": 60, \\\\\\"count\\\\\\": 1, \\\\\\"sum\\\\\\": 0.8, \\\\\\"bucket_counts\\\\\\": [0, 0, 1, 0], \\\\\\"explicit_bounds\\\\\\": [0.1, 0.5, 0.9, 1], \\\\\\"min\\\\\\": 0.8, \\\\\\"max\\\\\\": 0.8}]\\", \\"aggregation_temporality\\": 1}"}',
            point.to_json(),
        )
