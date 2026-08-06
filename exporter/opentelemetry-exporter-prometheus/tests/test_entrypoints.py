# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=no-self-use

import os
from unittest import TestCase
from unittest.mock import ANY, Mock, patch

from opentelemetry.exporter.prometheus import _AutoPrometheusMetricReader
from opentelemetry.sdk._configuration import _import_exporters
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_PROMETHEUS_HOST,
    OTEL_EXPORTER_PROMETHEUS_PORT,
)


class TestEntrypoints(TestCase):
    def test_import_exporters(self) -> None:
        """
        Tests that the entrypoint can be loaded and doesn't have a typo in the name
        """
        (
            _trace_exporters,
            metric_exporters,
            _logs_exporters,
        ) = _import_exporters(
            trace_exporter_names=[],
            metric_exporter_names=["prometheus"],
            log_exporter_names=[],
        )

        self.assertIs(
            metric_exporters["prometheus"],
            _AutoPrometheusMetricReader,
        )

    @patch("opentelemetry.exporter.prometheus.start_http_server")
    @patch.dict(os.environ)
    def test_starts_http_server_defaults(
        self, mock_start_http_server: Mock
    ) -> None:
        _AutoPrometheusMetricReader()
        mock_start_http_server.assert_called_once_with(
            port=9464, addr="localhost"
        )

    @patch("opentelemetry.exporter.prometheus.start_http_server")
    @patch.dict(os.environ, {OTEL_EXPORTER_PROMETHEUS_HOST: "1.2.3.4"})
    def test_starts_http_server_host_envvar(
        self, mock_start_http_server: Mock
    ) -> None:
        _AutoPrometheusMetricReader()
        mock_start_http_server.assert_called_once_with(
            port=ANY, addr="1.2.3.4"
        )

    @patch("opentelemetry.exporter.prometheus.start_http_server")
    @patch.dict(os.environ, {OTEL_EXPORTER_PROMETHEUS_PORT: "9999"})
    def test_starts_http_server_port_envvar(
        self, mock_start_http_server: Mock
    ) -> None:
        _AutoPrometheusMetricReader()
        mock_start_http_server.assert_called_once_with(port=9999, addr=ANY)
