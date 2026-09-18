# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Tests access private members of SDK classes to assert correct configuration.
# pylint: disable=protected-access

import logging
import os
import tempfile
import unittest
from unittest.mock import patch

import opentelemetry.configuration._config_provider as config_provider_module
from opentelemetry.configuration._config_provider import (
    ConfigProperties,
    get_config_provider,
)
from opentelemetry.configuration._sdk import configure_sdk
from opentelemetry.configuration.file import load_config_file
from opentelemetry.configuration.models import (
    ExperimentalGeneralInstrumentation,
    ExperimentalInstrumentation,
    OpenTelemetryConfiguration,
    SeverityNumber,
)
from opentelemetry.configuration.models import (
    Propagator as PropagatorConfig,
)
from opentelemetry.configuration.models import (
    Resource as ResourceConfig,
)
from opentelemetry.configuration.models import (
    SimpleSpanProcessor as SimpleSpanProcessorConfig,
)
from opentelemetry.configuration.models import (
    SpanExporter as SpanExporterConfig,
)
from opentelemetry.configuration.models import (
    SpanProcessor as SpanProcessorConfig,
)
from opentelemetry.configuration.models import (
    TracerProvider as TracerProviderConfig,
)
from opentelemetry.sdk.trace import TracerProvider as SdkTracerProvider
from opentelemetry.util._once import Once

_MIN_CONFIG_KWARGS = {"file_format": "1.0"}


def _config(**kwargs) -> OpenTelemetryConfiguration:
    return OpenTelemetryConfiguration(**{**_MIN_CONFIG_KWARGS, **kwargs})


def _configure_from_yaml(yaml_text: str) -> ConfigProperties:
    """Apply a configuration file and return the instrumentation view."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as temp_file:
        temp_file.write(yaml_text)
        config_path = temp_file.name
    try:
        configure_sdk(load_config_file(config_path))
    finally:
        os.unlink(config_path)
    return get_config_provider().get_instrumentation_config()


class TestConfigureSdk(unittest.TestCase):
    @patch("opentelemetry.configuration._sdk.configure_propagator")
    @patch("opentelemetry.configuration._sdk.configure_logger_provider")
    @patch("opentelemetry.configuration._sdk.configure_meter_provider")
    @patch("opentelemetry.configuration._sdk.configure_tracer_provider")
    @patch("opentelemetry.configuration._sdk.create_resource")
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
        mock_tracer.assert_called_once_with(tracer_cfg, sentinel_resource)
        mock_meter.assert_called_once_with(None, sentinel_resource)
        mock_logger.assert_called_once_with(None, sentinel_resource)
        mock_propagator.assert_called_once_with(propagator_cfg)

    @patch("opentelemetry.configuration._sdk.configure_propagator")
    @patch("opentelemetry.configuration._sdk.configure_logger_provider")
    @patch("opentelemetry.configuration._sdk.configure_meter_provider")
    @patch("opentelemetry.configuration._sdk.configure_tracer_provider")
    @patch("opentelemetry.configuration._sdk.create_resource")
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

    @patch("opentelemetry.configuration._sdk.configure_propagator")
    @patch("opentelemetry.configuration._sdk.configure_logger_provider")
    @patch("opentelemetry.configuration._sdk.configure_meter_provider")
    @patch("opentelemetry.configuration._sdk.configure_tracer_provider")
    @patch("opentelemetry.configuration._sdk.create_resource")
    def test_absent_sections_pass_none(
        self,
        mock_create_resource,
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


class TestConfigureSdkLogLevel(unittest.TestCase):
    def setUp(self):
        # Preserve whatever level was set before this test so we can
        # restore it in tearDown, keeping tests isolated from each other
        # and from the ambient logging configuration.
        self._original_level = logging.getLogger("opentelemetry").level

    def tearDown(self):
        logging.getLogger("opentelemetry").setLevel(self._original_level)

    @patch("opentelemetry.configuration._sdk.configure_propagator")
    @patch("opentelemetry.configuration._sdk.configure_logger_provider")
    @patch("opentelemetry.configuration._sdk.configure_meter_provider")
    @patch("opentelemetry.configuration._sdk.configure_tracer_provider")
    @patch("opentelemetry.configuration._sdk.create_resource")
    def test_sets_opentelemetry_logger_level(self, *_mocks):
        configure_sdk(_config(log_level=SeverityNumber.warn))
        self.assertEqual(logging.getLogger("opentelemetry").level, logging.WARNING)

    @patch("opentelemetry.configuration._sdk.configure_propagator")
    @patch("opentelemetry.configuration._sdk.configure_logger_provider")
    @patch("opentelemetry.configuration._sdk.configure_meter_provider")
    @patch("opentelemetry.configuration._sdk.configure_tracer_provider")
    @patch("opentelemetry.configuration._sdk.create_resource")
    def test_absent_log_level_leaves_logger_unchanged(self, *_mocks):
        logging.getLogger("opentelemetry").setLevel(logging.ERROR)
        configure_sdk(_config())
        self.assertEqual(logging.getLogger("opentelemetry").level, logging.ERROR)

    @patch("opentelemetry.configuration._sdk.configure_propagator")
    @patch("opentelemetry.configuration._sdk.configure_logger_provider")
    @patch("opentelemetry.configuration._sdk.configure_meter_provider")
    @patch("opentelemetry.configuration._sdk.configure_tracer_provider")
    @patch("opentelemetry.configuration._sdk.create_resource")
    def test_severity_number_variants_map_correctly(self, *_mocks):
        cases = [
            (SeverityNumber.trace, logging.DEBUG),
            (SeverityNumber.trace2, logging.DEBUG),
            (SeverityNumber.trace3, logging.DEBUG),
            (SeverityNumber.trace4, logging.DEBUG),
            (SeverityNumber.debug, logging.DEBUG),
            (SeverityNumber.debug2, logging.DEBUG),
            (SeverityNumber.debug3, logging.DEBUG),
            (SeverityNumber.debug4, logging.DEBUG),
            (SeverityNumber.info, logging.INFO),
            (SeverityNumber.info2, logging.INFO),
            (SeverityNumber.info3, logging.INFO),
            (SeverityNumber.info4, logging.INFO),
            (SeverityNumber.warn, logging.WARNING),
            (SeverityNumber.warn2, logging.WARNING),
            (SeverityNumber.warn3, logging.WARNING),
            (SeverityNumber.warn4, logging.WARNING),
            (SeverityNumber.error, logging.ERROR),
            (SeverityNumber.error2, logging.ERROR),
            (SeverityNumber.error3, logging.ERROR),
            (SeverityNumber.error4, logging.ERROR),
            (SeverityNumber.fatal, logging.CRITICAL),
            (SeverityNumber.fatal2, logging.CRITICAL),
            (SeverityNumber.fatal3, logging.CRITICAL),
            (SeverityNumber.fatal4, logging.CRITICAL),
        ]
        for severity, expected_level in cases:
            with self.subTest(severity=severity):
                configure_sdk(_config(log_level=severity))
                self.assertEqual(
                    logging.getLogger("opentelemetry").level,
                    expected_level,
                )

    def test_log_level_not_applied_when_disabled(self):
        logging.getLogger("opentelemetry").setLevel(logging.WARNING)
        configure_sdk(_config(disabled=True, log_level=SeverityNumber.error))
        self.assertEqual(logging.getLogger("opentelemetry").level, logging.WARNING)


class TestConfigureSdkIntegration(unittest.TestCase):
    """End-to-end: build a real OpenTelemetryConfiguration and apply it."""

    @patch("opentelemetry.configuration._tracer_provider.trace.set_tracer_provider")
    def test_applies_tracer_provider_globally(self, mock_set_tracer):
        config = _config(
            tracer_provider=TracerProviderConfig(
                processors=[
                    SpanProcessorConfig(simple=SimpleSpanProcessorConfig(exporter=SpanExporterConfig(console={})))
                ]
            )
        )

        configure_sdk(config)

        mock_set_tracer.assert_called_once()
        self.assertIsInstance(mock_set_tracer.call_args[0][0], SdkTracerProvider)


class TestConfigureSdkConfigProvider(unittest.TestCase):
    """The global ConfigProvider exposes the node as the file wrote it."""

    def setUp(self):
        config_provider_module._CONFIG_PROVIDER = None
        config_provider_module._CONFIG_PROVIDER_SET_ONCE = Once()

    def tearDown(self):
        config_provider_module._CONFIG_PROVIDER = None
        config_provider_module._CONFIG_PROVIDER_SET_ONCE = Once()

    def test_view_holds_only_the_keys_the_file_wrote(self):
        properties = _configure_from_yaml(
            'file_format: "1.0"\ninstrumentation/development:\n  general:\n    stability_opt_in_list: http\n'
        )

        self.assertEqual(properties.keys(), {"general"})
        # The typed model carries a field per language, so reading it would
        # report keys this file never mentioned.
        self.assertNotIn("cpp", properties)

    def test_key_written_as_null_is_present(self):
        properties = _configure_from_yaml(
            'file_format: "1.0"\ninstrumentation/development:\n  general:\n    stability_opt_in_list:\n'
        )

        general = properties.get_config("general")
        self.assertIn("stability_opt_in_list", general)
        self.assertIsNone(general.get_string("stability_opt_in_list"))

    def test_key_the_file_omitted_is_absent(self):
        properties = _configure_from_yaml(
            'file_format: "1.0"\n'
            "instrumentation/development:\n"
            "  general:\n"
            "    http:\n"
            "      semconv:\n"
            "        experimental: true\n"
        )

        general = properties.get_config("general")
        # Reading the typed model would report this key with a None value,
        # which is what a file writing an explicit null looks like.
        self.assertNotIn("stability_opt_in_list", general)

    def test_absent_node_yields_empty_view(self):
        properties = _configure_from_yaml('file_format: "1.0"\n')

        self.assertEqual(properties.keys(), set())

    def test_model_built_by_hand_falls_back_to_typed_node(self):
        configure_sdk(
            _config(
                instrumentation_development=ExperimentalInstrumentation(
                    general=ExperimentalGeneralInstrumentation(stability_opt_in_list="http")
                )
            )
        )

        properties = get_config_provider().get_instrumentation_config()
        general = properties.get_config("general")
        self.assertIsNotNone(general)
        self.assertEqual(general.get_string("stability_opt_in_list"), "http")
