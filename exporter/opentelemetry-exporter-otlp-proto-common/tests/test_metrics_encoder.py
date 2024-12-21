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

# pylint: disable=protected-access,too-many-lines
import unittest

from opentelemetry.exporter.otlp.proto.common._internal.metrics_encoder import (
    EncodingException,
)
from opentelemetry.exporter.otlp.proto.common.metrics_encoder import (
    encode_metrics,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import (
    AnyValue,
    InstrumentationScope,
    KeyValue,
)
from opentelemetry.proto.metrics.v1 import metrics_pb2 as pb2
from opentelemetry.proto.resource.v1.resource_pb2 import (
    Resource as OTLPResource,
)
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
from opentelemetry.test.metrictestutil import _generate_gauge, _generate_sum


class TestOTLPMetricsEncoder(unittest.TestCase):
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
        expected = ExportMetricsServiceRequest(
            resource_metrics=[
                pb2.ResourceMetrics(
                    schema_url="resource_schema_url",
                    resource=OTLPResource(
                        attributes=[
                            KeyValue(key="a", value=AnyValue(int_value=1)),
                            KeyValue(
                                key="b", value=AnyValue(bool_value=False)
                            ),
                        ]
                    ),
                    scope_metrics=[
                        pb2.ScopeMetrics(
                            scope=InstrumentationScope(
                                name="first_name", version="first_version"
                            ),
                            schema_url="instrumentation_scope_schema_url",
                            metrics=[
                                pb2.Metric(
                                    name="sum_int",
                                    unit="s",
                                    description="foo",
                                    sum=pb2.Sum(
                                        data_points=[
                                            pb2.NumberDataPoint(
                                                attributes=[
                                                    KeyValue(
                                                        key="a",
                                                        value=AnyValue(
                                                            int_value=1
                                                        ),
                                                    ),
                                                    KeyValue(
                                                        key="b",
                                                        value=AnyValue(
                                                            bool_value=True
                                                        ),
                                                    ),
                                                ],
                                                start_time_unix_nano=1641946015139533244,
                                                time_unix_nano=1641946016139533244,
                                                as_int=33,
                                            )
                                        ],
                                        aggregation_temporality=AggregationTemporality.CUMULATIVE,
                                        is_monotonic=True,
                                    ),
                                )
                            ],
                        )
                    ],
                )
            ]
        )
        actual = encode_metrics(metrics_data)
        self.assertEqual(expected, actual)

    def test_encode_sum_double(self):
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
                            metrics=[_generate_sum("sum_double", 2.98)],
                            schema_url="instrumentation_scope_schema_url",
                        )
                    ],
                    schema_url="resource_schema_url",
                )
            ]
        )
        expected = ExportMetricsServiceRequest(
            resource_metrics=[
                pb2.ResourceMetrics(
                    schema_url="resource_schema_url",
                    resource=OTLPResource(
                        attributes=[
                            KeyValue(key="a", value=AnyValue(int_value=1)),
                            KeyValue(
                                key="b", value=AnyValue(bool_value=False)
                            ),
                        ]
                    ),
                    scope_metrics=[
                        pb2.ScopeMetrics(
                            scope=InstrumentationScope(
                                name="first_name", version="first_version"
                            ),
                            schema_url="instrumentation_scope_schema_url",
                            metrics=[
                                pb2.Metric(
                                    name="sum_double",
                                    unit="s",
                                    description="foo",
                                    sum=pb2.Sum(
                                        data_points=[
                                            pb2.NumberDataPoint(
                                                attributes=[
                                                    KeyValue(
                                                        key="a",
                                                        value=AnyValue(
                                                            int_value=1
                                                        ),
                                                    ),
                                                    KeyValue(
                                                        key="b",
                                                        value=AnyValue(
                                                            bool_value=True
                                                        ),
                                                    ),
                                                ],
                                                start_time_unix_nano=1641946015139533244,
                                                time_unix_nano=1641946016139533244,
                                                as_double=2.98,
                                            )
                                        ],
                                        aggregation_temporality=AggregationTemporality.CUMULATIVE,
                                        is_monotonic=True,
                                    ),
                                )
                            ],
                        )
                    ],
                )
            ]
        )
        actual = encode_metrics(metrics_data)
        self.assertEqual(expected, actual)

    def test_encode_gauge_int(self):
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
                            metrics=[_generate_gauge("gauge_int", 9000)],
                            schema_url="instrumentation_scope_schema_url",
                        )
                    ],
                    schema_url="resource_schema_url",
                )
            ]
        )
        expected = ExportMetricsServiceRequest(
            resource_metrics=[
                pb2.ResourceMetrics(
                    schema_url="resource_schema_url",
                    resource=OTLPResource(
                        attributes=[
                            KeyValue(key="a", value=AnyValue(int_value=1)),
                            KeyValue(
                                key="b", value=AnyValue(bool_value=False)
                            ),
                        ]
                    ),
                    scope_metrics=[
                        pb2.ScopeMetrics(
                            scope=InstrumentationScope(
                                name="first_name", version="first_version"
                            ),
                            schema_url="instrumentation_scope_schema_url",
                            metrics=[
                                pb2.Metric(
                                    name="gauge_int",
                                    unit="s",
                                    description="foo",
                                    gauge=pb2.Gauge(
                                        data_points=[
                                            pb2.NumberDataPoint(
                                                attributes=[
                                                    KeyValue(
                                                        key="a",
                                                        value=AnyValue(
                                                            int_value=1
                                                        ),
                                                    ),
                                                    KeyValue(
                                                        key="b",
                                                        value=AnyValue(
                                                            bool_value=True
                                                        ),
                                                    ),
                                                ],
                                                time_unix_nano=1641946016139533244,
                                                start_time_unix_nano=0,
                                                as_int=9000,
                                            )
                                        ],
                                    ),
                                )
                            ],
                        )
                    ],
                )
            ]
        )
        actual = encode_metrics(metrics_data)
        self.assertEqual(expected, actual)

    def test_encode_gauge_double(self):
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
                            metrics=[_generate_gauge("gauge_double", 52.028)],
                            schema_url="instrumentation_scope_schema_url",
                        )
                    ],
                    schema_url="resource_schema_url",
                )
            ]
        )
        expected = ExportMetricsServiceRequest(
            resource_metrics=[
                pb2.ResourceMetrics(
                    schema_url="resource_schema_url",
                    resource=OTLPResource(
                        attributes=[
                            KeyValue(key="a", value=AnyValue(int_value=1)),
                            KeyValue(
                                key="b", value=AnyValue(bool_value=False)
                            ),
                        ]
                    ),
                    scope_metrics=[
                        pb2.ScopeMetrics(
                            scope=InstrumentationScope(
                                name="first_name", version="first_version"
                            ),
                            schema_url="instrumentation_scope_schema_url",
                            metrics=[
                                pb2.Metric(
                                    name="gauge_double",
                                    unit="s",
                                    description="foo",
                                    gauge=pb2.Gauge(
                                        data_points=[
                                            pb2.NumberDataPoint(
                                                attributes=[
                                                    KeyValue(
                                                        key="a",
                                                        value=AnyValue(
                                                            int_value=1
                                                        ),
                                                    ),
                                                    KeyValue(
                                                        key="b",
                                                        value=AnyValue(
                                                            bool_value=True
                                                        ),
                                                    ),
                                                ],
                                                time_unix_nano=1641946016139533244,
                                                as_double=52.028,
                                            )
                                        ],
                                    ),
                                )
                            ],
                        )
                    ],
                )
            ]
        )
        actual = encode_metrics(metrics_data)
        self.assertEqual(expected, actual)

    def test_encode_histogram(self):
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
        expected = ExportMetricsServiceRequest(
            resource_metrics=[
                pb2.ResourceMetrics(
                    schema_url="resource_schema_url",
                    resource=OTLPResource(
                        attributes=[
                            KeyValue(key="a", value=AnyValue(int_value=1)),
                            KeyValue(
                                key="b", value=AnyValue(bool_value=False)
                            ),
                        ]
                    ),
                    scope_metrics=[
                        pb2.ScopeMetrics(
                            scope=InstrumentationScope(
                                name="first_name", version="first_version"
                            ),
                            schema_url="instrumentation_scope_schema_url",
                            metrics=[
                                pb2.Metric(
                                    name="histogram",
                                    unit="s",
                                    description="foo",
                                    histogram=pb2.Histogram(
                                        data_points=[
                                            pb2.HistogramDataPoint(
                                                attributes=[
                                                    KeyValue(
                                                        key="a",
                                                        value=AnyValue(
                                                            int_value=1
                                                        ),
                                                    ),
                                                    KeyValue(
                                                        key="b",
                                                        value=AnyValue(
                                                            bool_value=True
                                                        ),
                                                    ),
                                                ],
                                                start_time_unix_nano=1641946016139533244,
                                                time_unix_nano=1641946016139533244,
                                                count=5,
                                                sum=67,
                                                bucket_counts=[1, 4],
                                                explicit_bounds=[10.0, 20.0],
                                                exemplars=[
                                                    pb2.Exemplar(
                                                        time_unix_nano=1641946016139533400,
                                                        as_double=298,
                                                        span_id=b"n\x0cc%}\xe3L\x92",
                                                        trace_id=b"\xd4\xcd\xa9[e/J\x15\x92\xb4I\xd5\x92\x9f\xda\x1b",
                                                        filtered_attributes=[
                                                            KeyValue(
                                                                key="filtered",
                                                                value=AnyValue(
                                                                    string_value="banana"
                                                                ),
                                                            )
                                                        ],
                                                    ),
                                                    pb2.Exemplar(
                                                        time_unix_nano=1641946016139533400,
                                                        as_double=298,
                                                        filtered_attributes=[
                                                            KeyValue(
                                                                key="filtered",
                                                                value=AnyValue(
                                                                    string_value="banana"
                                                                ),
                                                            )
                                                        ],
                                                    ),
                                                ],
                                                max=18.0,
                                                min=8.0,
                                            )
                                        ],
                                        aggregation_temporality=AggregationTemporality.DELTA,
                                    ),
                                )
                            ],
                        )
                    ],
                )
            ]
        )
        actual = encode_metrics(metrics_data)
        self.assertEqual(expected, actual)

    def test_encode_multiple_scope_histogram(self):
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
                            metrics=[self.histogram, self.histogram],
                            schema_url="instrumentation_scope_schema_url",
                        ),
                        ScopeMetrics(
                            scope=SDKInstrumentationScope(
                                name="second_name",
                                version="second_version",
                                schema_url="instrumentation_scope_schema_url",
                            ),
                            metrics=[self.histogram],
                            schema_url="instrumentation_scope_schema_url",
                        ),
                        ScopeMetrics(
                            scope=SDKInstrumentationScope(
                                name="third_name",
                                version="third_version",
                                schema_url="instrumentation_scope_schema_url",
                            ),
                            metrics=[self.histogram],
                            schema_url="instrumentation_scope_schema_url",
                        ),
                    ],
                    schema_url="resource_schema_url",
                )
            ]
        )
        expected = ExportMetricsServiceRequest(
            resource_metrics=[
                pb2.ResourceMetrics(
                    schema_url="resource_schema_url",
                    resource=OTLPResource(
                        attributes=[
                            KeyValue(key="a", value=AnyValue(int_value=1)),
                            KeyValue(
                                key="b", value=AnyValue(bool_value=False)
                            ),
                        ]
                    ),
                    scope_metrics=[
                        pb2.ScopeMetrics(
                            scope=InstrumentationScope(
                                name="first_name", version="first_version"
                            ),
                            schema_url="instrumentation_scope_schema_url",
                            metrics=[
                                pb2.Metric(
                                    name="histogram",
                                    unit="s",
                                    description="foo",
                                    histogram=pb2.Histogram(
                                        data_points=[
                                            pb2.HistogramDataPoint(
                                                attributes=[
                                                    KeyValue(
                                                        key="a",
                                                        value=AnyValue(
                                                            int_value=1
                                                        ),
                                                    ),
                                                    KeyValue(
                                                        key="b",
                                                        value=AnyValue(
                                                            bool_value=True
                                                        ),
                                                    ),
                                                ],
                                                start_time_unix_nano=1641946016139533244,
                                                time_unix_nano=1641946016139533244,
                                                count=5,
                                                sum=67,
                                                bucket_counts=[1, 4],
                                                explicit_bounds=[10.0, 20.0],
                                                exemplars=[
                                                    pb2.Exemplar(
                                                        time_unix_nano=1641946016139533400,
                                                        as_double=298,
                                                        span_id=b"n\x0cc%}\xe3L\x92",
                                                        trace_id=b"\xd4\xcd\xa9[e/J\x15\x92\xb4I\xd5\x92\x9f\xda\x1b",
                                                        filtered_attributes=[
                                                            KeyValue(
                                                                key="filtered",
                                                                value=AnyValue(
                                                                    string_value="banana"
                                                                ),
                                                            )
                                                        ],
                                                    ),
                                                    pb2.Exemplar(
                                                        time_unix_nano=1641946016139533400,
                                                        as_double=298,
                                                        filtered_attributes=[
                                                            KeyValue(
                                                                key="filtered",
                                                                value=AnyValue(
                                                                    string_value="banana"
                                                                ),
                                                            )
                                                        ],
                                                    ),
                                                ],
                                                max=18.0,
                                                min=8.0,
                                            )
                                        ],
                                        aggregation_temporality=AggregationTemporality.DELTA,
                                    ),
                                ),
                                pb2.Metric(
                                    name="histogram",
                                    unit="s",
                                    description="foo",
                                    histogram=pb2.Histogram(
                                        data_points=[
                                            pb2.HistogramDataPoint(
                                                attributes=[
                                                    KeyValue(
                                                        key="a",
                                                        value=AnyValue(
                                                            int_value=1
                                                        ),
                                                    ),
                                                    KeyValue(
                                                        key="b",
                                                        value=AnyValue(
                                                            bool_value=True
                                                        ),
                                                    ),
                                                ],
                                                start_time_unix_nano=1641946016139533244,
                                                time_unix_nano=1641946016139533244,
                                                count=5,
                                                sum=67,
                                                bucket_counts=[1, 4],
                                                explicit_bounds=[10.0, 20.0],
                                                exemplars=[
                                                    pb2.Exemplar(
                                                        time_unix_nano=1641946016139533400,
                                                        as_double=298,
                                                        span_id=b"n\x0cc%}\xe3L\x92",
                                                        trace_id=b"\xd4\xcd\xa9[e/J\x15\x92\xb4I\xd5\x92\x9f\xda\x1b",
                                                        filtered_attributes=[
                                                            KeyValue(
                                                                key="filtered",
                                                                value=AnyValue(
                                                                    string_value="banana"
                                                                ),
                                                            )
                                                        ],
                                                    ),
                                                    pb2.Exemplar(
                                                        time_unix_nano=1641946016139533400,
                                                        as_double=298,
                                                        filtered_attributes=[
                                                            KeyValue(
                                                                key="filtered",
                                                                value=AnyValue(
                                                                    string_value="banana"
                                                                ),
                                                            )
                                                        ],
                                                    ),
                                                ],
                                                max=18.0,
                                                min=8.0,
                                            )
                                        ],
                                        aggregation_temporality=AggregationTemporality.DELTA,
                                    ),
                                ),
                            ],
                        ),
                        pb2.ScopeMetrics(
                            scope=InstrumentationScope(
                                name="second_name", version="second_version"
                            ),
                            schema_url="instrumentation_scope_schema_url",
                            metrics=[
                                pb2.Metric(
                                    name="histogram",
                                    unit="s",
                                    description="foo",
                                    histogram=pb2.Histogram(
                                        data_points=[
                                            pb2.HistogramDataPoint(
                                                attributes=[
                                                    KeyValue(
                                                        key="a",
                                                        value=AnyValue(
                                                            int_value=1
                                                        ),
                                                    ),
                                                    KeyValue(
                                                        key="b",
                                                        value=AnyValue(
                                                            bool_value=True
                                                        ),
                                                    ),
                                                ],
                                                start_time_unix_nano=1641946016139533244,
                                                time_unix_nano=1641946016139533244,
                                                count=5,
                                                sum=67,
                                                bucket_counts=[1, 4],
                                                explicit_bounds=[10.0, 20.0],
                                                exemplars=[
                                                    pb2.Exemplar(
                                                        time_unix_nano=1641946016139533400,
                                                        as_double=298,
                                                        span_id=b"n\x0cc%}\xe3L\x92",
                                                        trace_id=b"\xd4\xcd\xa9[e/J\x15\x92\xb4I\xd5\x92\x9f\xda\x1b",
                                                        filtered_attributes=[
                                                            KeyValue(
                                                                key="filtered",
                                                                value=AnyValue(
                                                                    string_value="banana"
                                                                ),
                                                            )
                                                        ],
                                                    ),
                                                    pb2.Exemplar(
                                                        time_unix_nano=1641946016139533400,
                                                        as_double=298,
                                                        filtered_attributes=[
                                                            KeyValue(
                                                                key="filtered",
                                                                value=AnyValue(
                                                                    string_value="banana"
                                                                ),
                                                            )
                                                        ],
                                                    ),
                                                ],
                                                max=18.0,
                                                min=8.0,
                                            )
                                        ],
                                        aggregation_temporality=AggregationTemporality.DELTA,
                                    ),
                                )
                            ],
                        ),
                        pb2.ScopeMetrics(
                            scope=InstrumentationScope(
                                name="third_name", version="third_version"
                            ),
                            schema_url="instrumentation_scope_schema_url",
                            metrics=[
                                pb2.Metric(
                                    name="histogram",
                                    unit="s",
                                    description="foo",
                                    histogram=pb2.Histogram(
                                        data_points=[
                                            pb2.HistogramDataPoint(
                                                attributes=[
                                                    KeyValue(
                                                        key="a",
                                                        value=AnyValue(
                                                            int_value=1
                                                        ),
                                                    ),
                                                    KeyValue(
                                                        key="b",
                                                        value=AnyValue(
                                                            bool_value=True
                                                        ),
                                                    ),
                                                ],
                                                start_time_unix_nano=1641946016139533244,
                                                time_unix_nano=1641946016139533244,
                                                count=5,
                                                sum=67,
                                                bucket_counts=[1, 4],
                                                explicit_bounds=[10.0, 20.0],
                                                exemplars=[
                                                    pb2.Exemplar(
                                                        time_unix_nano=1641946016139533400,
                                                        as_double=298,
                                                        span_id=b"n\x0cc%}\xe3L\x92",
                                                        trace_id=b"\xd4\xcd\xa9[e/J\x15\x92\xb4I\xd5\x92\x9f\xda\x1b",
                                                        filtered_attributes=[
                                                            KeyValue(
                                                                key="filtered",
                                                                value=AnyValue(
                                                                    string_value="banana"
                                                                ),
                                                            )
                                                        ],
                                                    ),
                                                    pb2.Exemplar(
                                                        time_unix_nano=1641946016139533400,
                                                        as_double=298,
                                                        filtered_attributes=[
                                                            KeyValue(
                                                                key="filtered",
                                                                value=AnyValue(
                                                                    string_value="banana"
                                                                ),
                                                            )
                                                        ],
                                                    ),
                                                ],
                                                max=18.0,
                                                min=8.0,
                                            )
                                        ],
                                        aggregation_temporality=AggregationTemporality.DELTA,
                                    ),
                                )
                            ],
                        ),
                    ],
                )
            ]
        )
        actual = encode_metrics(metrics_data)
        self.assertEqual(expected, actual)

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
        expected = ExportMetricsServiceRequest(
            resource_metrics=[
                pb2.ResourceMetrics(
                    schema_url="resource_schema_url",
                    resource=OTLPResource(
                        attributes=[
                            KeyValue(key="a", value=AnyValue(int_value=1)),
                            KeyValue(
                                key="b", value=AnyValue(bool_value=False)
                            ),
                        ]
                    ),
                    scope_metrics=[
                        pb2.ScopeMetrics(
                            scope=InstrumentationScope(
                                name="first_name", version="first_version"
                            ),
                            schema_url="instrumentation_scope_schema_url",
                            metrics=[
                                pb2.Metric(
                                    name="exponential_histogram",
                                    unit="unit",
                                    description="description",
                                    exponential_histogram=pb2.ExponentialHistogram(
                                        data_points=[
                                            pb2.ExponentialHistogramDataPoint(
                                                attributes=[
                                                    KeyValue(
                                                        key="a",
                                                        value=AnyValue(
                                                            int_value=1
                                                        ),
                                                    ),
                                                    KeyValue(
                                                        key="b",
                                                        value=AnyValue(
                                                            bool_value=True
                                                        ),
                                                    ),
                                                ],
                                                start_time_unix_nano=0,
                                                time_unix_nano=1,
                                                count=2,
                                                sum=3,
                                                scale=4,
                                                zero_count=5,
                                                positive=pb2.ExponentialHistogramDataPoint.Buckets(
                                                    offset=6,
                                                    bucket_counts=[7, 8],
                                                ),
                                                negative=pb2.ExponentialHistogramDataPoint.Buckets(
                                                    offset=9,
                                                    bucket_counts=[10, 11],
                                                ),
                                                flags=12,
                                                exemplars=[],
                                                min=13.0,
                                                max=14.0,
                                            )
                                        ],
                                        aggregation_temporality=AggregationTemporality.DELTA,
                                    ),
                                )
                            ],
                        )
                    ],
                )
            ]
        )
        # pylint: disable=protected-access
        actual = encode_metrics(metrics_data)
        self.assertEqual(expected, actual)

    def test_encoding_exception_reraise(self):
        # this number is too big to fit in a signed 64-bit proto field and causes a ValueError
        big_number = 2**63
        metrics_data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Resource(
                        attributes={},
                        schema_url="resource_schema_url",
                    ),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=SDKInstrumentationScope(
                                name="first_name",
                                version="first_version",
                                schema_url="instrumentation_scope_schema_url",
                            ),
                            metrics=[_generate_sum("sum_double", big_number)],
                            schema_url="instrumentation_scope_schema_url",
                        )
                    ],
                    schema_url="resource_schema_url",
                )
            ]
        )
        with self.assertRaises(EncodingException) as context:
            encode_metrics(metrics_data)

        # assert that the EncodingException wraps the metric and original exception
        assert isinstance(context.exception.metric, Metric)
        assert isinstance(context.exception.original_exception, ValueError)

    def test_encode_scope_with_attributes(self):
        metrics_data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Resource(
                        attributes=None,
                        schema_url="resource_schema_url",
                    ),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=SDKInstrumentationScope(
                                name="first_name",
                                version="first_version",
                                schema_url="instrumentation_scope_schema_url",
                                attributes={"one": 1, "two": "2"},
                            ),
                            metrics=[_generate_sum("sum_int", 88)],
                            schema_url="instrumentation_scope_schema_url",
                        )
                    ],
                    schema_url="resource_schema_url",
                )
            ]
        )
        expected = ExportMetricsServiceRequest(
            resource_metrics=[
                pb2.ResourceMetrics(
                    schema_url="resource_schema_url",
                    resource=OTLPResource(),
                    scope_metrics=[
                        pb2.ScopeMetrics(
                            scope=InstrumentationScope(
                                name="first_name",
                                version="first_version",
                                attributes=[
                                    KeyValue(
                                        key="one", value=AnyValue(int_value=1)
                                    ),
                                    KeyValue(
                                        key="two",
                                        value=AnyValue(string_value="2"),
                                    ),
                                ],
                            ),
                            schema_url="instrumentation_scope_schema_url",
                            metrics=[
                                pb2.Metric(
                                    name="sum_int",
                                    unit="s",
                                    description="foo",
                                    sum=pb2.Sum(
                                        data_points=[
                                            pb2.NumberDataPoint(
                                                attributes=[
                                                    KeyValue(
                                                        key="a",
                                                        value=AnyValue(
                                                            int_value=1
                                                        ),
                                                    ),
                                                    KeyValue(
                                                        key="b",
                                                        value=AnyValue(
                                                            bool_value=True
                                                        ),
                                                    ),
                                                ],
                                                start_time_unix_nano=1641946015139533244,
                                                time_unix_nano=1641946016139533244,
                                                as_int=88,
                                            )
                                        ],
                                        aggregation_temporality=AggregationTemporality.CUMULATIVE,
                                        is_monotonic=True,
                                    ),
                                )
                            ],
                        )
                    ],
                )
            ]
        )
        actual = encode_metrics(metrics_data)
        self.assertEqual(expected, actual)
