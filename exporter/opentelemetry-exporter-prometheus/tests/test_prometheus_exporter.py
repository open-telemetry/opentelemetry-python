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

from os import environ
from textwrap import dedent
from unittest import TestCase
from unittest.mock import Mock, patch

from prometheus_client import generate_latest
from prometheus_client.core import (
    CounterMetricFamily,
    GaugeMetricFamily,
    InfoMetricFamily,
)

from opentelemetry.exporter.prometheus import (
    PrometheusMetricReader,
    _CustomCollector,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_PYTHON_EXPERIMENTAL_DISABLE_PROMETHEUS_UNIT_NORMALIZATION,
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
from opentelemetry.sdk.resources import Resource
from opentelemetry.test.metrictestutil import (
    _generate_gauge,
    _generate_histogram,
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

    def verify_text_format(
        self, metric: Metric, expect_prometheus_text: str
    ) -> None:
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

        collector = _CustomCollector(disable_target_info=True)
        collector.add_metrics_data(metrics_data)
        result_bytes = generate_latest(collector)
        result = result_bytes.decode("utf-8")
        self.assertEqual(result, expect_prometheus_text)

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
        self.verify_text_format(
            metric,
            dedent(
                """\
                # HELP test_name_seconds foo
                # TYPE test_name_seconds histogram
                test_name_seconds_bucket{histo="1",le="123.0"} 1.0
                test_name_seconds_bucket{histo="1",le="456.0"} 4.0
                test_name_seconds_bucket{histo="1",le="+Inf"} 6.0
                test_name_seconds_count{histo="1"} 6.0
                test_name_seconds_sum{histo="1"} 579.0
                """
            ),
        )

    def test_monotonic_sum_to_prometheus(self):
        labels = {"environment@": "staging", "os": "Windows"}
        metric = _generate_sum(
            "test@sum_monotonic",
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

        collector = _CustomCollector(disable_target_info=True)
        collector.add_metrics_data(metrics_data)

        for prometheus_metric in collector.collect():
            self.assertEqual(type(prometheus_metric), CounterMetricFamily)
            self.assertEqual(
                prometheus_metric.name, "test_sum_monotonic_testunit"
            )
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

    def test_non_monotonic_sum_to_prometheus(self):
        labels = {"environment@": "staging", "os": "Windows"}
        metric = _generate_sum(
            "test@sum_nonmonotonic",
            123,
            attributes=labels,
            description="testdesc",
            unit="testunit",
            is_monotonic=False,
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

        collector = _CustomCollector(disable_target_info=True)
        collector.add_metrics_data(metrics_data)

        for prometheus_metric in collector.collect():
            self.assertEqual(type(prometheus_metric), GaugeMetricFamily)
            self.assertEqual(
                prometheus_metric.name, "test_sum_nonmonotonic_testunit"
            )
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

        collector = _CustomCollector(disable_target_info=True)
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
        collector = _CustomCollector(disable_target_info=True)
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

    def test_target_info_enabled_by_default(self):
        metric_reader = PrometheusMetricReader()
        provider = MeterProvider(
            metric_readers=[metric_reader],
            resource=Resource({"os": "Unix", "version": "1.2.3"}),
        )
        meter = provider.get_meter("getting-started", "0.1.2")
        counter = meter.create_counter("counter")
        counter.add(1)
        result = list(metric_reader._collector.collect())

        self.assertEqual(len(result), 2)

        prometheus_metric = result[0]

        self.assertEqual(type(prometheus_metric), InfoMetricFamily)
        self.assertEqual(prometheus_metric.name, "target")
        self.assertEqual(prometheus_metric.documentation, "Target metadata")
        self.assertTrue(len(prometheus_metric.samples) == 1)
        self.assertEqual(prometheus_metric.samples[0].value, 1)
        self.assertTrue(len(prometheus_metric.samples[0].labels) == 2)
        self.assertEqual(prometheus_metric.samples[0].labels["os"], "Unix")
        self.assertEqual(
            prometheus_metric.samples[0].labels["version"], "1.2.3"
        )

    def test_target_info_disabled(self):
        metric_reader = PrometheusMetricReader(disable_target_info=True)
        provider = MeterProvider(
            metric_readers=[metric_reader],
            resource=Resource({"os": "Unix", "version": "1.2.3"}),
        )
        meter = provider.get_meter("getting-started", "0.1.2")
        counter = meter.create_counter("counter")
        counter.add(1)
        result = list(metric_reader._collector.collect())

        for prometheus_metric in result:
            self.assertNotEqual(type(prometheus_metric), InfoMetricFamily)
            self.assertNotEqual(prometheus_metric.name, "target")
            self.assertNotEqual(
                prometheus_metric.documentation, "Target metadata"
            )
            self.assertNotIn("os", prometheus_metric.samples[0].labels)
            self.assertNotIn("version", prometheus_metric.samples[0].labels)

    def test_target_info_sanitize(self):
        metric_reader = PrometheusMetricReader()
        provider = MeterProvider(
            metric_readers=[metric_reader],
            resource=Resource(
                {
                    "system.os": "Unix",
                    "system.name": "Prometheus Target Sanitize",
                    "histo": 1,
                    "ratio": 0.1,
                }
            ),
        )
        meter = provider.get_meter("getting-started", "0.1.2")
        counter = meter.create_counter("counter")
        counter.add(1)
        prometheus_metric = list(metric_reader._collector.collect())[0]

        self.assertEqual(type(prometheus_metric), InfoMetricFamily)
        self.assertEqual(prometheus_metric.name, "target")
        self.assertEqual(prometheus_metric.documentation, "Target metadata")
        self.assertTrue(len(prometheus_metric.samples) == 1)
        self.assertEqual(prometheus_metric.samples[0].value, 1)
        self.assertTrue(len(prometheus_metric.samples[0].labels) == 4)
        self.assertTrue("system_os" in prometheus_metric.samples[0].labels)
        self.assertEqual(
            prometheus_metric.samples[0].labels["system_os"], "Unix"
        )
        self.assertTrue("system_name" in prometheus_metric.samples[0].labels)
        self.assertEqual(
            prometheus_metric.samples[0].labels["system_name"],
            "Prometheus Target Sanitize",
        )
        self.assertTrue("histo" in prometheus_metric.samples[0].labels)
        self.assertEqual(
            prometheus_metric.samples[0].labels["histo"],
            "1",
        )
        self.assertTrue("ratio" in prometheus_metric.samples[0].labels)
        self.assertEqual(
            prometheus_metric.samples[0].labels["ratio"],
            "0.1",
        )

    def test_label_order_does_not_matter(self):
        metric_reader = PrometheusMetricReader()
        provider = MeterProvider(metric_readers=[metric_reader])
        meter = provider.get_meter("getting-started", "0.1.2")
        counter = meter.create_counter("counter")

        counter.add(1, {"cause": "cause1", "reason": "reason1"})
        counter.add(1, {"reason": "reason2", "cause": "cause2"})

        prometheus_output = generate_latest().decode()

        # All labels are mapped correctly
        self.assertIn('cause="cause1"', prometheus_output)
        self.assertIn('cause="cause2"', prometheus_output)
        self.assertIn('reason="reason1"', prometheus_output)
        self.assertIn('reason="reason2"', prometheus_output)

        # Only one metric is generated
        metric_count = prometheus_output.count("# HELP counter_total")
        self.assertEqual(metric_count, 1)

    def test_metric_name(self):
        self.verify_text_format(
            _generate_sum(name="test_counter", value=1, unit=""),
            dedent(
                """\
                # HELP test_counter_total foo
                # TYPE test_counter_total counter
                test_counter_total{a="1",b="true"} 1.0
                """
            ),
        )
        self.verify_text_format(
            _generate_sum(name="1leading_digit", value=1, unit=""),
            dedent(
                """\
                # HELP _leading_digit_total foo
                # TYPE _leading_digit_total counter
                _leading_digit_total{a="1",b="true"} 1.0
                """
            ),
        )
        self.verify_text_format(
            _generate_sum(name="!@#counter_invalid_chars", value=1, unit=""),
            dedent(
                """\
                # HELP _counter_invalid_chars_total foo
                # TYPE _counter_invalid_chars_total counter
                _counter_invalid_chars_total{a="1",b="true"} 1.0
                """
            ),
        )

    def test_metric_name_with_unit(self):
        self.verify_text_format(
            _generate_gauge(name="test.metric.no_unit", value=1, unit=""),
            dedent(
                """\
                # HELP test_metric_no_unit foo
                # TYPE test_metric_no_unit gauge
                test_metric_no_unit{a="1",b="true"} 1.0
                """
            ),
        )
        self.verify_text_format(
            _generate_gauge(
                name="test.metric.spaces", value=1, unit="   \t  "
            ),
            dedent(
                """\
                # HELP test_metric_spaces foo
                # TYPE test_metric_spaces gauge
                test_metric_spaces{a="1",b="true"} 1.0
                """
            ),
        )

        # UCUM annotations should be stripped
        self.verify_text_format(
            _generate_sum(name="test_counter", value=1, unit="{requests}"),
            dedent(
                """\
                # HELP test_counter_total foo
                # TYPE test_counter_total counter
                test_counter_total{a="1",b="true"} 1.0
                """
            ),
        )

        # slash converts to "per"
        self.verify_text_format(
            _generate_gauge(name="test_gauge", value=1, unit="m/s"),
            dedent(
                """\
                # HELP test_gauge_meters_per_second foo
                # TYPE test_gauge_meters_per_second gauge
                test_gauge_meters_per_second{a="1",b="true"} 1.0
                """
            ),
        )

        # invalid characters in name are sanitized before being passed to prom client, which
        # would throw errors
        self.verify_text_format(
            _generate_sum(name="test_counter", value=1, unit="%{foo}@?"),
            dedent(
                """\
                # HELP test_counter_total foo
                # TYPE test_counter_total counter
                test_counter_total{a="1",b="true"} 1.0
                """
            ),
        )

    # TODO(#3929): remove this opt-out option
    @patch.dict(
        environ,
        {
            OTEL_PYTHON_EXPERIMENTAL_DISABLE_PROMETHEUS_UNIT_NORMALIZATION: "true"
        },
    )
    def test_metric_name_with_unit_normalization_disabled(self):
        self.verify_text_format(
            _generate_sum(name="test_unit_not_normalized", value=1, unit="s"),
            dedent(
                """\
                # HELP test_unit_not_normalized_s_total foo
                # TYPE test_unit_not_normalized_s_total counter
                test_unit_not_normalized_s_total{a="1",b="true"} 1.0
                """
            ),
        )

    def test_semconv(self):
        """Tests that a few select semconv metrics get converted to the expected prometheus
        text format"""
        self.verify_text_format(
            _generate_sum(
                name="system.filesystem.usage",
                value=1,
                is_monotonic=False,
                unit="By",
            ),
            dedent(
                """\
                # HELP system_filesystem_usage_bytes foo
                # TYPE system_filesystem_usage_bytes gauge
                system_filesystem_usage_bytes{a="1",b="true"} 1.0
                """
            ),
        )
        self.verify_text_format(
            _generate_sum(
                name="system.network.dropped",
                value=1,
                unit="{packets}",
            ),
            dedent(
                """\
                # HELP system_network_dropped_total foo
                # TYPE system_network_dropped_total counter
                system_network_dropped_total{a="1",b="true"} 1.0
                """
            ),
        )
        self.verify_text_format(
            _generate_histogram(
                name="http.server.request.duration",
                unit="s",
            ),
            dedent(
                """\
                # HELP http_server_request_duration_seconds foo
                # TYPE http_server_request_duration_seconds histogram
                http_server_request_duration_seconds_bucket{a="1",b="true",le="123.0"} 1.0
                http_server_request_duration_seconds_bucket{a="1",b="true",le="456.0"} 4.0
                http_server_request_duration_seconds_bucket{a="1",b="true",le="+Inf"} 6.0
                http_server_request_duration_seconds_count{a="1",b="true"} 6.0
                http_server_request_duration_seconds_sum{a="1",b="true"} 579.0
                """
            ),
        )
        self.verify_text_format(
            _generate_sum(
                name="http.server.active_requests",
                value=1,
                unit="{request}",
                is_monotonic=False,
            ),
            dedent(
                """\
                # HELP http_server_active_requests foo
                # TYPE http_server_active_requests gauge
                http_server_active_requests{a="1",b="true"} 1.0
                """
            ),
        )
        # if the metric name already contains the unit, it shouldn't be added again
        self.verify_text_format(
            _generate_sum(
                name="metric_name_with_myunit",
                value=1,
                unit="myunit",
            ),
            dedent(
                """\
                # HELP metric_name_with_myunit_total foo
                # TYPE metric_name_with_myunit_total counter
                metric_name_with_myunit_total{a="1",b="true"} 1.0
                """
            ),
        )
        self.verify_text_format(
            _generate_gauge(
                name="metric_name_percent",
                value=1,
                unit="%",
            ),
            dedent(
                """\
                # HELP metric_name_percent foo
                # TYPE metric_name_percent gauge
                metric_name_percent{a="1",b="true"} 1.0
                """
            ),
        )
