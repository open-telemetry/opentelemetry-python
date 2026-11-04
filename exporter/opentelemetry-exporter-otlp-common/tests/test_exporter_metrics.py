# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from opentelemetry.exporter.otlp.common._exporter_metrics import (
    ExporterMetrics,
    NoOpExporterMetrics,
    create_exporter_metrics,
)
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OtelComponentTypeValues,
)
from opentelemetry.semconv.attributes.server_attributes import (
    SERVER_ADDRESS,
    SERVER_PORT,
)


class TestExporterMetrics(unittest.TestCase):
    def test_factory_returns_noop_when_disabled(self):
        meter_provider = Mock()

        with patch("opentelemetry.exporter.otlp.common._exporter_metrics.get_meter_provider") as get_meter_provider:
            metrics = create_exporter_metrics(
                OtelComponentTypeValues.OTLP_HTTP_SPAN_EXPORTER,
                "traces",
                "http://localhost:4318/v1/traces",
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
            "http://localhost:4318/v1/traces",
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

    def test_grpc_uses_static_port(self):
        meter_provider = Mock()
        meter_provider.get_meter.return_value = Mock()

        cases: list[tuple[OtelComponentTypeValues, str, str, int]] = [
            (
                OtelComponentTypeValues.OTLP_GRPC_SPAN_EXPORTER,
                "http://otlp.example.com",
                "otlp.example.com",
                443,
            ),
            (
                OtelComponentTypeValues.OTLP_GRPC_LOG_EXPORTER,
                "https://otlp.example.com",
                "otlp.example.com",
                443,
            ),
            (
                OtelComponentTypeValues.OTLP_GRPC_METRIC_EXPORTER,
                "otlp.example.com:4317",
                "otlp.example.com",
                4317,
            ),
            (
                OtelComponentTypeValues.OTLP_GRPC_SPAN_EXPORTER,
                "http://localhost:4317",
                "localhost",
                4317,
            ),
        ]

        for component_type, endpoint, expected_address, expected_port in cases:
            with self.subTest(component_type=component_type, endpoint=endpoint):
                metrics = ExporterMetrics(component_type, "traces", endpoint, meter_provider)
                # pylint: disable-next=protected-access
                self.assertEqual(metrics._standard_attrs[SERVER_ADDRESS], expected_address)
                # pylint: disable-next=protected-access
                self.assertEqual(metrics._standard_attrs[SERVER_PORT], expected_port)

    def test_http_port_defaults_by_scheme(self):
        meter_provider = Mock()
        meter_provider.get_meter.return_value = Mock()

        cases: list[tuple[str, int]] = [
            ("http://otlp.example.com", 80),
            ("https://otlp.example.com", 443),
        ]

        for endpoint, expected_port in cases:
            with self.subTest(endpoint=endpoint):
                metrics = ExporterMetrics(
                    OtelComponentTypeValues.OTLP_HTTP_SPAN_EXPORTER,
                    "traces",
                    endpoint,
                    meter_provider,
                )
                # pylint: disable-next=protected-access
                self.assertEqual(metrics._standard_attrs[SERVER_ADDRESS], "otlp.example.com")
                # pylint: disable-next=protected-access
                self.assertEqual(metrics._standard_attrs[SERVER_PORT], expected_port)
