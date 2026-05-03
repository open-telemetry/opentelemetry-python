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
from unittest.mock import Mock, patch
from urllib.parse import urlparse

from opentelemetry.exporter.otlp.proto.common._exporter_metrics import (
    ExporterMetrics,
    NoOpExporterMetrics,
    create_exporter_metrics,
)
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OtelComponentTypeValues,
)


class TestExporterMetrics(unittest.TestCase):
    def test_factory_returns_noop_when_disabled(self):
        meter_provider = Mock()

        with patch(
            "opentelemetry.exporter.otlp.proto.common."
            "_exporter_metrics.get_meter_provider"
        ) as get_meter_provider:
            metrics = create_exporter_metrics(
                "traces",
                urlparse("http://localhost:4318/v1/traces"),
                meter_provider,
                False,
                component_type=OtelComponentTypeValues.OTLP_HTTP_SPAN_EXPORTER,
            )

        self.assertIsInstance(metrics, NoOpExporterMetrics)
        meter_provider.get_meter.assert_not_called()
        get_meter_provider.assert_not_called()

    def test_factory_returns_exporter_metrics_when_enabled(self):
        meter_provider = Mock()
        meter_provider.get_meter.return_value = Mock()

        metrics = create_exporter_metrics(
            "traces",
            urlparse("http://localhost:4318/v1/traces"),
            meter_provider,
            True,
            component_type=OtelComponentTypeValues.OTLP_HTTP_SPAN_EXPORTER,
        )

        self.assertIsInstance(metrics, ExporterMetrics)
        meter_provider.get_meter.assert_called_once_with("opentelemetry-sdk")

    def test_noop_export_operation_yields_result(self):
        metrics = NoOpExporterMetrics()

        with metrics.export_operation(1) as result:
            result.error = RuntimeError("error")

        self.assertIsInstance(result.error, RuntimeError)


if __name__ == "__main__":
    unittest.main()
