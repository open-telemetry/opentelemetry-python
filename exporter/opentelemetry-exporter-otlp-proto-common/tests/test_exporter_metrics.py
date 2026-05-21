# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

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
                OtelComponentTypeValues.OTLP_HTTP_SPAN_EXPORTER,
                "traces",
                urlparse("http://localhost:4318/v1/traces"),
                meter_provider,
                False,
            )

        self.assertIsInstance(metrics, NoOpExporterMetrics)
        meter_provider.get_meter.assert_not_called()
        get_meter_provider.assert_not_called()

    def test_factory_returns_exporter_metrics_when_enabled(self):
        meter_provider = Mock()
        meter_provider.get_meter.return_value = Mock()

        metrics = create_exporter_metrics(
            OtelComponentTypeValues.OTLP_HTTP_SPAN_EXPORTER,
            "traces",
            urlparse("http://localhost:4318/v1/traces"),
            meter_provider,
            True,
        )

        self.assertIsInstance(metrics, ExporterMetrics)
        meter_provider.get_meter.assert_called_once_with("opentelemetry-sdk")

    def test_noop_export_operation_yields_result(self):
        metrics = NoOpExporterMetrics()

        with metrics.export_operation(1) as result:
            result.error = RuntimeError("error")

        self.assertIsInstance(result.error, RuntimeError)
