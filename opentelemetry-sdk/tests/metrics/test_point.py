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

from opentelemetry.sdk._metrics.point import Gauge, Histogram, Metric, Sum
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope


def _create_metric(value):
    return Metric(
        attributes={"attr-key": "test-val"},
        description="test-description",
        instrumentation_scope=InstrumentationScope(
            name="name", version="version"
        ),
        name="test-name",
        resource=Resource({"resource-key": "resource-val"}),
        unit="test-unit",
        point=value,
    )


class TestDatapointToJSON(TestCase):
    def test_sum(self):
        self.maxDiff = None
        point = _create_metric(
            Sum(
                aggregation_temporality=2,
                is_monotonic=True,
                start_time_unix_nano=10,
                time_unix_nano=20,
                value=9,
            )
        )
        self.assertEqual(
            '{"attributes": {"attr-key": "test-val"}, "description": "test-description", "instrumentation_scope": "InstrumentationScope(name, version, None)", "name": "test-name", "resource": "BoundedAttributes({\'resource-key\': \'resource-val\'}, maxlen=None)", "unit": "test-unit", "point": {"aggregation_temporality": 2, "is_monotonic": true, "start_time_unix_nano": 10, "time_unix_nano": 20, "value": 9}}',
            point.to_json(),
        )

    def test_gauge(self):
        point = _create_metric(Gauge(time_unix_nano=40, value=20))
        self.assertEqual(
            '{"attributes": {"attr-key": "test-val"}, "description": "test-description", "instrumentation_scope": "InstrumentationScope(name, version, None)", "name": "test-name", "resource": "BoundedAttributes({\'resource-key\': \'resource-val\'}, maxlen=None)", "unit": "test-unit", "point": {"time_unix_nano": 40, "value": 20}}',
            point.to_json(),
        )

    def test_histogram(self):
        point = _create_metric(
            Histogram(
                aggregation_temporality=1,
                bucket_counts=[0, 0, 1, 0],
                explicit_bounds=[0.1, 0.5, 0.9, 1],
                max=0.8,
                min=0.8,
                start_time_unix_nano=50,
                sum=0.8,
                time_unix_nano=60,
            )
        )
        self.maxDiff = None
        self.assertEqual(
            '{"attributes": {"attr-key": "test-val"}, "description": "test-description", "instrumentation_scope": "InstrumentationScope(name, version, None)", "name": "test-name", "resource": "BoundedAttributes({\'resource-key\': \'resource-val\'}, maxlen=None)", "unit": "test-unit", "point": {"aggregation_temporality": 1, "bucket_counts": [0, 0, 1, 0], "explicit_bounds": [0.1, 0.5, 0.9, 1], "max": 0.8, "min": 0.8, "start_time_unix_nano": 50, "sum": 0.8, "time_unix_nano": 60}}',
            point.to_json(),
        )
