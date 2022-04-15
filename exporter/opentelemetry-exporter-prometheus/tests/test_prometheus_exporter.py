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

import unittest
from textwrap import dedent
from unittest import mock

from prometheus_client import generate_latest
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily

from opentelemetry.exporter.prometheus import (
    PrometheusMetricReader,
    _CustomCollector,
)
from opentelemetry.sdk._metrics.point import AggregationTemporality, Histogram
from opentelemetry.test.metrictestutil import (
    _generate_gauge,
    _generate_metric,
    _generate_sum,
    _generate_unsupported_metric,
)


class TestPrometheusMetricReader(unittest.TestCase):
    def setUp(self):
        self._mock_registry_register = mock.Mock()
        self._registry_register_patch = mock.patch(
            "prometheus_client.core.REGISTRY.register",
            side_effect=self._mock_registry_register,
        )

    # pylint: disable=protected-access
    def test_constructor(self):
        """Test the constructor."""
        with self._registry_register_patch:
            exporter = PrometheusMetricReader("testprefix")
            self.assertEqual(exporter._collector._prefix, "testprefix")
            self.assertTrue(self._mock_registry_register.called)

    def test_shutdown(self):
        with mock.patch(
            "prometheus_client.core.REGISTRY.unregister"
        ) as registry_unregister_patch:
            exporter = PrometheusMetricReader()
            exporter.shutdown()
            self.assertTrue(registry_unregister_patch.called)

    def test_histogram_to_prometheus(self):
        record = _generate_metric(
            "test@name",
            Histogram(
                aggregation_temporality=AggregationTemporality.CUMULATIVE,
                bucket_counts=[1, 3, 2],
                explicit_bounds=[123.0, 456.0],
                start_time_unix_nano=1641946016139533244,
                max=457,
                min=1,
                sum=579.0,
                time_unix_nano=1641946016139533244,
            ),
            attributes={"histo": 1},
        )

        collector = _CustomCollector("testprefix")
        collector.add_metrics_data([record])
        result_bytes = generate_latest(collector)
        result = result_bytes.decode("utf-8")
        self.assertEqual(
            result,
            dedent(
                """\
                # HELP testprefix_test_name_s foo
                # TYPE testprefix_test_name_s histogram
                testprefix_test_name_s_bucket{histo="1",le="123.0"} 1.0
                testprefix_test_name_s_bucket{histo="1",le="456.0"} 4.0
                testprefix_test_name_s_bucket{histo="1",le="+Inf"} 6.0
                testprefix_test_name_s_count{histo="1"} 6.0
                testprefix_test_name_s_sum{histo="1"} 579.0
                """
            ),
        )

    def test_sum_to_prometheus(self):
        labels = {"environment@": "staging", "os": "Windows"}
        record = _generate_sum(
            "test@sum",
            123,
            attributes=labels,
            description="testdesc",
            unit="testunit",
        )
        collector = _CustomCollector("testprefix")
        collector.add_metrics_data([record])

        for prometheus_metric in collector.collect():
            self.assertEqual(type(prometheus_metric), CounterMetricFamily)
            self.assertEqual(
                prometheus_metric.name, "testprefix_test_sum_testunit"
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
        record = _generate_gauge(
            "test@gauge",
            123,
            attributes=labels,
            description="testdesc",
            unit="testunit",
        )
        collector = _CustomCollector("testprefix")
        collector.add_metrics_data([record])

        for prometheus_metric in collector.collect():
            self.assertEqual(type(prometheus_metric), GaugeMetricFamily)
            self.assertEqual(
                prometheus_metric.name, "testprefix_test_gauge_testunit"
            )
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
        collector = _CustomCollector("testprefix")
        collector.add_metrics_data([record])
        collector.collect()
        self.assertLogs("opentelemetry.exporter.prometheus", level="WARNING")

    def test_sanitize(self):
        collector = _CustomCollector("testprefix")
        self.assertEqual(
            collector._sanitize("1!2@3#4$5%6^7&8*9(0)_-"),
            "1_2_3_4_5_6_7_8_9_0___",
        )
        self.assertEqual(collector._sanitize(",./?;:[]{}"), "__________")
        self.assertEqual(collector._sanitize("TestString"), "TestString")
        self.assertEqual(collector._sanitize("aAbBcC_12_oi"), "aAbBcC_12_oi")
