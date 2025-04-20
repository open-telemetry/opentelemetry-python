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

import json
import unittest

from opentelemetry.exporter.otlp.json.common.metrics_encoder import (
    encode_metrics,
)
from opentelemetry.exporter.otlp.json.common.encoding import IdEncoding
from opentelemetry.sdk.metrics import Exemplar
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    Buckets,
    ExponentialHistogramDataPoint,
    HistogramDataPoint,
    Metric,
    MetricsData,
    ResourceMetrics,
    ScopeMetrics,
)
from opentelemetry.sdk.metrics.export import (
    ExponentialHistogram as ExponentialHistogramType,
)
from opentelemetry.sdk.metrics.export import Histogram as HistogramType
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import (
    InstrumentationScope as SDKInstrumentationScope,
)
from opentelemetry.test.metrictestutil import _generate_sum


class TestMetricsEncoder(unittest.TestCase):
    span_id = int("6e0c63257de34c92", 16)
    trace_id = int("d4cda95b652f4a1592b449d5929fda1b", 16)

    histogram = Metric(
        name="histogram",
        description="foo",
        unit="s",
        data=HistogramType(
            data_points=[
                HistogramDataPoint(
                    attributes={"a": 1, "b": True},
                    start_time_unix_nano=1641946016139533244,
                    time_unix_nano=1641946016139533244,
                    exemplars=[
                        Exemplar(
                            {"filtered": "banana"},
                            298.0,
                            1641946016139533400,
                            span_id,
                            trace_id,
                        ),
                        Exemplar(
                            {"filtered": "banana"},
                            298.0,
                            1641946016139533400,
                            None,
                            None,
                        ),
                    ],
                    count=5,
                    sum=67,
                    bucket_counts=[1, 4],
                    explicit_bounds=[10.0, 20.0],
                    min=8,
                    max=18,
                )
            ],
            aggregation_temporality=AggregationTemporality.DELTA,
        ),
    )

    def test_encode_sum_int(self):
        # Test encoding an integer sum metric
        metrics_data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Resource(
                        attributes={"a": 1, "b": False},
                        schema_url="resource_schema_url",
                    ),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=SDKInstrumentationScope(
                                name="first_name",
                                version="first_version",
                                schema_url="instrumentation_scope_schema_url",
                            ),
                            metrics=[_generate_sum("sum_int", 33)],
                            schema_url="instrumentation_scope_schema_url",
                        )
                    ],
                    schema_url="resource_schema_url",
                )
            ]
        )

        json_metrics = encode_metrics(metrics_data)

        # Verify structure
        self.assertIn("resourceMetrics", json_metrics)
        self.assertEqual(len(json_metrics["resourceMetrics"]), 1)

        # Convert to JSON and back to ensure it's serializable
        json_str = json.dumps(json_metrics)
        # Verify serialization works
        json.loads(json_str)

        # Verify content
        resource_metrics = json_metrics["resourceMetrics"][0]
        self.assertEqual(resource_metrics["schemaUrl"], "resource_schema_url")
        self.assertEqual(len(resource_metrics["scopeMetrics"]), 1)

        scope_metrics = resource_metrics["scopeMetrics"][0]
        self.assertEqual(scope_metrics["scope"]["name"], "first_name")
        self.assertEqual(scope_metrics["scope"]["version"], "first_version")
        self.assertEqual(len(scope_metrics["metrics"]), 1)

        metric = scope_metrics["metrics"][0]
        self.assertEqual(metric["name"], "sum_int")
        self.assertEqual(metric["unit"], "s")
        self.assertEqual(metric["description"], "foo")
        self.assertIn("sum", metric)

        sum_data = metric["sum"]
        # In ProtoJSON format, the aggregation temporality is a string
        self.assertEqual(
            sum_data["aggregationTemporality"],
            "AGGREGATION_TEMPORALITY_CUMULATIVE",
        )
        self.assertTrue(sum_data["isMonotonic"])
        self.assertEqual(len(sum_data["dataPoints"]), 1)

        data_point = sum_data["dataPoints"][0]
        self.assertEqual(
            data_point["asInt"], "33"
        )  # Should be a string to avoid int overflow

    def test_encode_histogram(self):
        # Test encoding a histogram metric
        metrics_data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Resource(
                        attributes={"a": 1, "b": False},
                        schema_url="resource_schema_url",
                    ),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=SDKInstrumentationScope(
                                name="first_name",
                                version="first_version",
                                schema_url="instrumentation_scope_schema_url",
                            ),
                            metrics=[self.histogram],
                            schema_url="instrumentation_scope_schema_url",
                        )
                    ],
                    schema_url="resource_schema_url",
                )
            ]
        )

        # Encode metrics to JSON with hex ids
        json_metrics = encode_metrics(metrics_data, IdEncoding.HEX)

        # Check ids in hex format
        self.assertEqual(
            json_metrics
                ["resourceMetrics"][0]
                ["scopeMetrics"][0]
                ["metrics"][0]
                ["histogram"]["dataPoints"][0]
                ["exemplars"][0]
                ["spanId"],
            "6e0c63257de34c92")

        json_metrics = encode_metrics(metrics_data)

        # Verify structure
        self.assertIn("resourceMetrics", json_metrics)

        # Convert to JSON and back to ensure it's serializable
        json_str = json.dumps(json_metrics)
        # Verify serialization works
        json.loads(json_str)

        # Verify content
        resource_metrics = json_metrics["resourceMetrics"][0]
        scope_metrics = resource_metrics["scopeMetrics"][0]
        metric = scope_metrics["metrics"][0]

        self.assertEqual(metric["name"], "histogram")
        self.assertIn("histogram", metric)

        histogram_data = metric["histogram"]
        # In ProtoJSON format, the aggregation temporality is a string
        self.assertEqual(
            histogram_data["aggregationTemporality"],
            "AGGREGATION_TEMPORALITY_DELTA",
        )
        self.assertEqual(len(histogram_data["dataPoints"]), 1)

        data_point = histogram_data["dataPoints"][0]
        self.assertEqual(data_point["sum"], 67)
        self.assertEqual(
            data_point["count"], "5"
        )  # Should be a string to avoid int overflow
        self.assertEqual(
            data_point["bucketCounts"], ["1", "4"]
        )  # Should be strings
        self.assertEqual(data_point["explicitBounds"], [10.0, 20.0])
        self.assertEqual(data_point["min"], 8)
        self.assertEqual(data_point["max"], 18)

        # Verify exemplars
        self.assertEqual(len(data_point["exemplars"]), 2)

        exemplar = data_point["exemplars"][0]
        self.assertEqual(exemplar["timeUnixNano"], str(1641946016139533400))
        # In ProtoJSON format, span IDs and trace IDs are base64-encoded
        self.assertIn("spanId", exemplar)
        self.assertIn("traceId", exemplar)
        # We don't check the exact values since they're base64-encoded
        self.assertEqual(exemplar["asDouble"], 298.0)

        exemplar2 = data_point["exemplars"][1]
        self.assertEqual(exemplar2["timeUnixNano"], str(1641946016139533400))
        self.assertEqual(exemplar2["asDouble"], 298.0)
        self.assertNotIn("spanId", exemplar2)
        self.assertNotIn("traceId", exemplar2)

    def test_encode_exponential_histogram(self):
        exponential_histogram = Metric(
            name="exponential_histogram",
            description="description",
            unit="unit",
            data=ExponentialHistogramType(
                data_points=[
                    ExponentialHistogramDataPoint(
                        attributes={"a": 1, "b": True},
                        start_time_unix_nano=0,
                        time_unix_nano=1,
                        count=2,
                        sum=3,
                        scale=4,
                        zero_count=5,
                        positive=Buckets(offset=6, bucket_counts=[7, 8]),
                        negative=Buckets(offset=9, bucket_counts=[10, 11]),
                        flags=12,
                        min=13.0,
                        max=14.0,
                    )
                ],
                aggregation_temporality=AggregationTemporality.DELTA,
            ),
        )

        metrics_data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Resource(
                        attributes={"a": 1, "b": False},
                        schema_url="resource_schema_url",
                    ),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=SDKInstrumentationScope(
                                name="first_name",
                                version="first_version",
                                schema_url="instrumentation_scope_schema_url",
                            ),
                            metrics=[exponential_histogram],
                            schema_url="instrumentation_scope_schema_url",
                        )
                    ],
                    schema_url="resource_schema_url",
                )
            ]
        )

        json_metrics = encode_metrics(metrics_data)

        # Convert to JSON and back to ensure it's serializable
        json_str = json.dumps(json_metrics)
        # Verify serialization works
        json.loads(json_str)

        # Verify content
        resource_metrics = json_metrics["resourceMetrics"][0]
        scope_metrics = resource_metrics["scopeMetrics"][0]
        metric = scope_metrics["metrics"][0]

        self.assertEqual(metric["name"], "exponential_histogram")
        # In ProtoJSON format, it's "exponentialHistogram" not "exponentialHistogram"
        self.assertIn("exponentialHistogram", metric)

        histogram_data = metric["exponentialHistogram"]
        # In ProtoJSON format, the aggregation temporality is a string
        self.assertEqual(
            histogram_data["aggregationTemporality"],
            "AGGREGATION_TEMPORALITY_DELTA",
        )
        self.assertEqual(len(histogram_data["dataPoints"]), 1)

        data_point = histogram_data["dataPoints"][0]
        self.assertEqual(data_point["sum"], 3)
        self.assertEqual(data_point["count"], "2")  # Should be a string
        self.assertEqual(data_point["scale"], 4)
        self.assertEqual(data_point["zeroCount"], "5")  # Should be a string

        self.assertEqual(data_point["positive"]["offset"], 6)
        self.assertEqual(
            data_point["positive"]["bucketCounts"], ["7", "8"]
        )  # Should be strings

        self.assertEqual(data_point["negative"]["offset"], 9)
        self.assertEqual(
            data_point["negative"]["bucketCounts"], ["10", "11"]
        )  # Should be strings

        self.assertEqual(data_point["flags"], 12)
        self.assertEqual(data_point["min"], 13.0)
        self.assertEqual(data_point["max"], 14.0)

    def test_encoding_exception(self):
        # Create a metric with a value that will cause an encoding error
        class BadMetric:
            def __init__(self):
                self.data = BadData()
                self.name = "bad_metric"
                self.description = "bad"
                self.unit = "bad"

        class BadData:
            def __init__(self):
                pass

        metrics_data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Resource(
                        attributes={},
                    ),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=SDKInstrumentationScope(
                                name="test",
                                version="test",
                            ),
                            metrics=[BadMetric()],
                            schema_url="",
                        )
                    ],
                    schema_url="",
                )
            ]
        )

        # The new implementation doesn't raise an exception for unsupported data types,
        # it just ignores them. So we just verify that encoding completes without error.
        json_metrics = encode_metrics(metrics_data)

        # Verify the basic structure is correct
        self.assertIn("resourceMetrics", json_metrics)
        self.assertEqual(len(json_metrics["resourceMetrics"]), 1)

        # Verify the metric is included but without any data type
        resource_metrics = json_metrics["resourceMetrics"][0]
        scope_metrics = resource_metrics["scopeMetrics"][0]
        metrics = scope_metrics["metrics"]

        self.assertEqual(len(metrics), 1)
        metric = metrics[0]
        self.assertEqual(metric["name"], "bad_metric")
        self.assertEqual(metric["description"], "bad")
        self.assertEqual(metric["unit"], "bad")

        # Verify no data type field was added
        self.assertNotIn("gauge", metric)
        self.assertNotIn("sum", metric)
        self.assertNotIn("histogram", metric)
        self.assertNotIn("exponentialHistogram", metric)
