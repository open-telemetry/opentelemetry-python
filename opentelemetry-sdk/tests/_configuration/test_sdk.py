# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Tests access private members of SDK classes to assert correct configuration.
# pylint: disable=protected-access

import unittest
from unittest.mock import patch

from opentelemetry.sdk._configuration._sdk import configure_sdk
from opentelemetry.sdk._configuration.models import (
    OpenTelemetryConfiguration,
)
from opentelemetry.sdk._configuration.models import (
    Propagator as PropagatorConfig,
)
from opentelemetry.sdk._configuration.models import (
    Resource as ResourceConfig,
)
from opentelemetry.sdk._configuration.models import (
    SimpleSpanProcessor as SimpleSpanProcessorConfig,
)
from opentelemetry.sdk._configuration.models import (
    SpanExporter as SpanExporterConfig,
)
from opentelemetry.sdk._configuration.models import (
    SpanProcessor as SpanProcessorConfig,
)
from opentelemetry.sdk._configuration.models import (
    TracerProvider as TracerProviderConfig,
)
from opentelemetry.sdk.trace import TracerProvider as SdkTracerProvider

_MIN_CONFIG_KWARGS = {"file_format": "1.0"}


def _config(**kwargs) -> OpenTelemetryConfiguration:
    return OpenTelemetryConfiguration(**{**_MIN_CONFIG_KWARGS, **kwargs})


class TestConfigureSdk(unittest.TestCase):
    @patch("opentelemetry.sdk._configuration._sdk.configure_propagator")
    @patch("opentelemetry.sdk._configuration._sdk.configure_logger_provider")
    @patch("opentelemetry.sdk._configuration._sdk.configure_meter_provider")
    @patch("opentelemetry.sdk._configuration._sdk.configure_tracer_provider")
    @patch("opentelemetry.sdk._configuration._sdk.create_resource")
    # pylint: disable=no-self-use
    def test_calls_each_signal_with_resource(
        self,
        mock_create_resource,
        mock_tracer,
        mock_meter,
        mock_logger,
        mock_propagator,
    ):
        sentinel_resource = object()
        mock_create_resource.return_value = sentinel_resource

        resource_cfg = ResourceConfig()
        tracer_cfg = TracerProviderConfig(processors=[])
        propagator_cfg = PropagatorConfig()
        config = _config(
            resource=resource_cfg,
            tracer_provider=tracer_cfg,
            propagator=propagator_cfg,
        )

        configure_sdk(config)

        mock_create_resource.assert_called_once_with(resource_cfg)
        mock_tracer.assert_called_once_with(tracer_cfg, sentinel_resource, None)
        mock_meter.assert_called_once_with(None, sentinel_resource)
        mock_logger.assert_called_once_with(None, sentinel_resource, None)
        mock_propagator.assert_called_once_with(propagator_cfg)

    @patch("opentelemetry.sdk._configuration._sdk.configure_propagator")
    @patch("opentelemetry.sdk._configuration._sdk.configure_logger_provider")
    @patch("opentelemetry.sdk._configuration._sdk.configure_meter_provider")
    @patch("opentelemetry.sdk._configuration._sdk.configure_tracer_provider")
    @patch("opentelemetry.sdk._configuration._sdk.create_resource")
    # pylint: disable=no-self-use
    def test_disabled_skips_everything(
        self,
        mock_create_resource,
        mock_tracer,
        mock_meter,
        mock_logger,
        mock_propagator,
    ):
        config = _config(
            disabled=True,
            tracer_provider=TracerProviderConfig(processors=[]),
        )

        configure_sdk(config)

        mock_create_resource.assert_not_called()
        mock_tracer.assert_not_called()
        mock_meter.assert_not_called()
        mock_logger.assert_not_called()
        mock_propagator.assert_not_called()

    @patch("opentelemetry.sdk._configuration._sdk.configure_propagator")
    @patch("opentelemetry.sdk._configuration._sdk.configure_logger_provider")
    @patch("opentelemetry.sdk._configuration._sdk.configure_meter_provider")
    @patch("opentelemetry.sdk._configuration._sdk.configure_tracer_provider")
    @patch("opentelemetry.sdk._configuration._sdk.create_resource")
    def test_absent_sections_pass_none(
        self,
        mock_create_resource,  # noqa: ARG002
        mock_tracer,
        mock_meter,
        mock_logger,
        mock_propagator,
    ):
        configure_sdk(_config())

        # Each configure_* is called exactly once, with config=None.
        self.assertEqual(mock_tracer.call_args.args[0], None)
        self.assertEqual(mock_meter.call_args.args[0], None)
        self.assertEqual(mock_logger.call_args.args[0], None)
        self.assertEqual(mock_propagator.call_args.args[0], None)


class TestConfigureSdkIntegration(unittest.TestCase):
    """End-to-end: build a real OpenTelemetryConfiguration and apply it."""

    @patch(
        "opentelemetry.sdk._configuration._tracer_provider.trace.set_tracer_provider"
    )
    def test_applies_tracer_provider_globally(self, mock_set_tracer):
        config = _config(
            tracer_provider=TracerProviderConfig(
                processors=[
                    SpanProcessorConfig(
                        simple=SimpleSpanProcessorConfig(
                            exporter=SpanExporterConfig(console={})
                        )
                    )
                ]
            )
        )

        configure_sdk(config)

        mock_set_tracer.assert_called_once()
        self.assertIsInstance(
            mock_set_tracer.call_args[0][0], SdkTracerProvider
        )
