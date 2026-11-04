# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Tests access private members of SDK providers to assert wired configuration.
# pylint: disable=protected-access

import unittest
from pathlib import Path

from opentelemetry.configuration._logger_provider import (
    create_logger_provider,
)
from opentelemetry.configuration._meter_provider import (
    create_meter_provider,
)
from opentelemetry.configuration._tracer_provider import (
    create_tracer_provider,
)
from opentelemetry.configuration.file import load_config_file
from opentelemetry.configuration.models import (
    ExperimentalLoggerConfig,
    ExperimentalLoggerConfigurator,
    ExperimentalLoggerMatcherAndConfig,
    ExperimentalMeterConfig,
    ExperimentalMeterConfigurator,
    ExperimentalMeterMatcherAndConfig,
    ExperimentalTracerConfig,
    ExperimentalTracerConfigurator,
    ExperimentalTracerMatcherAndConfig,
)
from opentelemetry.sdk.util.instrumentation import InstrumentationScope


class TestConfiguratorYaml(unittest.TestCase):
    """Verify the tracer/meter/logger configurator nodes are parsed from YAML
    and wired into the providers they configure."""

    @classmethod
    def setUpClass(cls):
        config_path = Path(__file__).parent / "data" / "configurator_config.yaml"
        cls.config = load_config_file(str(config_path))

    def test_tracer_configurator_parsed_from_yaml(self):
        self.assertEqual(
            self.config.tracer_provider.tracer_configurator_development,
            ExperimentalTracerConfigurator(
                default_config=ExperimentalTracerConfig(enabled=True),
                tracers=[
                    ExperimentalTracerMatcherAndConfig(
                        name="noisy.*",
                        config=ExperimentalTracerConfig(enabled=False),
                    )
                ],
            ),
        )

    def test_meter_configurator_parsed_from_yaml(self):
        self.assertEqual(
            self.config.meter_provider.meter_configurator_development,
            ExperimentalMeterConfigurator(
                default_config=ExperimentalMeterConfig(enabled=False),
                meters=[
                    ExperimentalMeterMatcherAndConfig(
                        name="keep.*",
                        config=ExperimentalMeterConfig(enabled=True),
                    )
                ],
            ),
        )

    def test_logger_configurator_parsed_from_yaml(self):
        self.assertEqual(
            self.config.logger_provider.logger_configurator_development,
            ExperimentalLoggerConfigurator(
                default_config=ExperimentalLoggerConfig(enabled=True),
                loggers=[
                    ExperimentalLoggerMatcherAndConfig(
                        name="noisy.*",
                        config=ExperimentalLoggerConfig(enabled=False),
                    )
                ],
            ),
        )

    def test_tracer_configurator_from_yaml_is_wired(self):
        provider = create_tracer_provider(self.config.tracer_provider)
        self.assertFalse(provider._apply_tracer_configurator(InstrumentationScope("noisy.http")).is_enabled)
        self.assertTrue(provider._apply_tracer_configurator(InstrumentationScope("app.service")).is_enabled)

    def test_meter_configurator_from_yaml_is_wired(self):
        provider = create_meter_provider(self.config.meter_provider)
        self.assertTrue(provider._apply_meter_configurator(InstrumentationScope("keep.me")).is_enabled)
        self.assertFalse(provider._apply_meter_configurator(InstrumentationScope("other")).is_enabled)

    def test_logger_configurator_from_yaml_is_wired(self):
        provider = create_logger_provider(self.config.logger_provider)
        self.assertFalse(provider._apply_logger_configurator(InstrumentationScope("noisy.http")).is_enabled)
        self.assertTrue(provider._apply_logger_configurator(InstrumentationScope("app.service")).is_enabled)
