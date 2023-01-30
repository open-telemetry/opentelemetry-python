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

from textwrap import dedent
from unittest import TestCase
from unittest.mock import Mock, patch

from prometheus_client import generate_latest
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily

from opentelemetry.exporter.prometheus import (
    PrometheusMetricReader,
    _CustomCollector,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    Histogram,
    HistogramDataPoint,
    Metric,
    MetricsData,
    ResourceMetrics,
    ScopeMetrics,
)
from opentelemetry.test.metrictestutil import (
    _generate_gauge,
    _generate_sum,
    _generate_unsupported_metric,
)


class TestPrometheusMetricReader(TestCase):
    def setUp(self):
        self._mock_registry_register = Mock()
        self._registry_register_patch = patch(
            "prometheus_client.core.REGISTRY.register",
            side_effect=self._mock_registry_register,
        )

    # pylint: disable=protected-access
    def test_constructor(self):
        """Test the constructor."""
        with self._registry_register_patch:
            _ = PrometheusMetricReader()
            self.assertTrue(self._mock_registry_register.called)

    def test_shutdown(self):
        with patch(
            "prometheus_client.core.REGISTRY.unregister"
        ) as registry_unregister_patch:
            exporter = PrometheusMetricReader()
            exporter.shutdown()
            self.assertTrue(registry_unregister_patch.called)

    def test_histogram_to_prometheus(self):
        metric = Metric(
            name="test@name",
            description="foo",
            unit="s",
            data=Histogram(
                data_points=[
                    HistogramDataPoint(
                        attributes={"histo": 1},
                        start_time_unix_nano=1641946016139533244,
                        time_unix_nano=1641946016139533244,
                        count=6,
                        sum=579.0,
                        bucket_counts=[1, 3, 2],
                        explicit_bounds=[123.0, 456.0],
                        min=1,
                        max=457,
                    )
                ],
                aggregation_temporality=AggregationTemporality.DELTA,
            ),
        )
        metrics_data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Mock(),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=Mock(),
                            metrics=[metric],
                            schema_url="schema_url",
                        )
                    ],
                    schema_url="schema_url",
                )
            ]
        )

        collector = _CustomCollector()
        collector.add_metrics_data(metrics_data)
        result_bytes = generate_latest(collector)
        result = result_bytes.decode("utf-8")
        self.assertEqual(
            result,
            dedent(
                """\
                # HELP test_name_s foo
                # TYPE test_name_s histogram
                test_name_s_bucket{histo="1",le="123.0"} 1.0
                test_name_s_bucket{histo="1",le="456.0"} 4.0
                test_name_s_bucket{histo="1",le="+Inf"} 6.0
                test_name_s_count{histo="1"} 6.0
                test_name_s_sum{histo="1"} 579.0
                """
            ),
        )

    def test_sum_to_prometheus(self):
        labels = {"environment@": "staging", "os": "Windows"}
        metric = _generate_sum(
            "test@sum",
            123,
            attributes=labels,
            description="testdesc",
            unit="testunit",
        )

        metrics_data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Mock(),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=Mock(),
                            metrics=[metric],
                            schema_url="schema_url",
                        )
                    ],
                    schema_url="schema_url",
                )
            ]
        )

        collector = _CustomCollector()
        collector.add_metrics_data(metrics_data)

        for prometheus_metric in collector.collect():
            self.assertEqual(type(prometheus_metric), CounterMetricFamily)
            self.assertEqual(prometheus_metric.name, "test_sum_testunit")
            self.assertEqual(prometheus_metric.documentation, "testdesc")
            self.assertTrue(len(prometheus_metric.samples) == 1)
            self.assertEqual(prometheus_metric.samples[0].value, 123)
            self.assertTrue(len(prometheus_metric.samples[0].labels) == 2)
            self.assertEqual(
                prometheus_metric.samples[0].labels["environment_"], "staging"
            )
            self.assertEqual(
                prometheus_metric.samples[0].labels["os"], "Windows"
            )

    def test_gauge_to_prometheus(self):
        labels = {"environment@": "dev", "os": "Unix"}
        metric = _generate_gauge(
            "test@gauge",
            123,
            attributes=labels,
            description="testdesc",
            unit="testunit",
        )

        metrics_data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Mock(),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=Mock(),
                            metrics=[metric],
                            schema_url="schema_url",
                        )
                    ],
                    schema_url="schema_url",
                )
            ]
        )

        collector = _CustomCollector()
        collector.add_metrics_data(metrics_data)

        for prometheus_metric in collector.collect():
            self.assertEqual(type(prometheus_metric), GaugeMetricFamily)
            self.assertEqual(prometheus_metric.name, "test_gauge_testunit")
            self.assertEqual(prometheus_metric.documentation, "testdesc")
            self.assertTrue(len(prometheus_metric.samples) == 1)
            self.assertEqual(prometheus_metric.samples[0].value, 123)
            self.assertTrue(len(prometheus_metric.samples[0].labels) == 2)
            self.assertEqual(
                prometheus_metric.samples[0].labels["environment_"], "dev"
            )
            self.assertEqual(prometheus_metric.samples[0].labels["os"], "Unix")

    def test_invalid_metric(self):
        labels = {"environment": "staging"}
        record = _generate_unsupported_metric(
            "tesname",
            attributes=labels,
            description="testdesc",
            unit="testunit",
        )
        collector = _CustomCollector()
        collector.add_metrics_data([record])
        collector.collect()
        self.assertLogs("opentelemetry.exporter.prometheus", level="WARNING")

    def test_sanitize(self):
        collector = _CustomCollector()
        self.assertEqual(
            collector._sanitize("1!2@3#4$5%6^7&8*9(0)_-"),
            "1_2_3_4_5_6_7_8_9_0___",
        )
        self.assertEqual(collector._sanitize(",./?;:[]{}"), "__________")
        self.assertEqual(collector._sanitize("TestString"), "TestString")
        self.assertEqual(collector._sanitize("aAbBcC_12_oi"), "aAbBcC_12_oi")

    def test_list_labels(self):
        labels = {"environment@": ["1", "2", "3"], "os": "Unix"}
        metric = _generate_gauge(
            "test@gauge",
            123,
            attributes=labels,
            description="testdesc",
            unit="testunit",
        )
        metrics_data = MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Mock(),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=Mock(),
                            metrics=[metric],
                            schema_url="schema_url",
                        )
                    ],
                    schema_url="schema_url",
                )
            ]
        )
        collector = _CustomCollector()
        collector.add_metrics_data(metrics_data)

        for prometheus_metric in collector.collect():
            self.assertEqual(type(prometheus_metric), GaugeMetricFamily)
            self.assertEqual(prometheus_metric.name, "test_gauge_testunit")
            self.assertEqual(prometheus_metric.documentation, "testdesc")
            self.assertTrue(len(prometheus_metric.samples) == 1)
            self.assertEqual(prometheus_metric.samples[0].value, 123)
            self.assertTrue(len(prometheus_metric.samples[0].labels) == 2)
            self.assertEqual(
                prometheus_metric.samples[0].labels["environment_"],
                '["1", "2", "3"]',
            )
            self.assertEqual(prometheus_metric.samples[0].labels["os"], "Unix")

    def test_check_value(self):

        collector = _CustomCollector()

        self.assertEqual(collector._check_value(1), "1")
        self.assertEqual(collector._check_value(1.0), "1.0")
        self.assertEqual(collector._check_value("a"), "a")
        self.assertEqual(collector._check_value([1, 2]), "[1, 2]")
        self.assertEqual(collector._check_value((1, 2)), "[1, 2]")
        self.assertEqual(collector._check_value(["a", 2]), '["a", 2]')
        self.assertEqual(collector._check_value(True), "true")
        self.assertEqual(collector._check_value(False), "false")
        self.assertEqual(collector._check_value(None), "null")

    def test_multiple_collection_calls(self):

        metric_reader = PrometheusMetricReader()
        provider = MeterProvider(metric_readers=[metric_reader])
        meter = provider.get_meter("getting-started", "0.1.2")
        counter = meter.create_counter("counter")
        counter.add(1)
        result_0 = list(metric_reader._collector.collect())
        result_1 = list(metric_reader._collector.collect())
        result_2 = list(metric_reader._collector.collect())
        self.assertEqual(result_0, result_1)
        self.assertEqual(result_1, result_2)
