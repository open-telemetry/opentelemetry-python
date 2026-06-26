# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Tests access private members of SDK classes to assert correct configuration.
# pylint: disable=protected-access,no-self-use

import types
import unittest
from unittest.mock import MagicMock, patch

from opentelemetry.sdk._configuration import _OTelSDKConfigurator
from opentelemetry.sdk.environment_variables import OTEL_CONFIG_FILE


class _FakeConfigurationModule(types.ModuleType):
    """Stub `opentelemetry.configuration` module.

    The SDK lazy-imports this package at runtime when OTEL_CONFIG_FILE is set,
    but the SDK's test env does not depend on opentelemetry-configuration.
    Injecting an instance into sys.modules lets these tests exercise the
    routing without installing the downstream package. Declaring the attrs
    at class level lets pylint introspect them without a no-member disable.
    """

    configure_sdk: MagicMock
    load_config_file: MagicMock

    def __init__(self) -> None:
        super().__init__("opentelemetry.configuration")
        self.configure_sdk = MagicMock()
        self.load_config_file = MagicMock()


class TestConfiguratorFileRouting(unittest.TestCase):
    def tearDown(self):
        # _BaseConfigurator caches instances via a singleton; reset so sibling
        # tests (e.g. test_configurator.py's CustomConfigurator subclass) are
        # not affected by this class's singleton state.
        _OTelSDKConfigurator._instance = None

    @patch.dict("os.environ", {}, clear=True)
    @patch("opentelemetry.sdk._configuration._initialize_components")
    def test_env_var_unset_runs_env_var_path(self, mock_init_components):
        _OTelSDKConfigurator()._configure(auto_instrumentation_version="X")
        mock_init_components.assert_called_once_with(
            auto_instrumentation_version="X"
        )

    @patch.dict("os.environ", {OTEL_CONFIG_FILE: "/tmp/otel.yaml"})
    @patch("opentelemetry.sdk._configuration._initialize_components")
    def test_env_var_set_routes_to_declarative_path(
        self, mock_init_components
    ):
        fake = _FakeConfigurationModule()
        sentinel_config = object()
        fake.load_config_file.return_value = sentinel_config

        with patch.dict("sys.modules", {"opentelemetry.configuration": fake}):
            _OTelSDKConfigurator()._configure()

        fake.load_config_file.assert_called_once_with("/tmp/otel.yaml")
        fake.configure_sdk.assert_called_once_with(sentinel_config)
        mock_init_components.assert_not_called()

    @patch.dict("os.environ", {OTEL_CONFIG_FILE: "/tmp/otel.yaml"})
    @patch.dict(
        "sys.modules", {"opentelemetry.configuration": None}, clear=False
    )
    @patch("opentelemetry.sdk._configuration._initialize_components")
    def test_env_var_set_but_package_missing_raises(
        self, mock_init_components
    ):
        # When opentelemetry-configuration is not installed but the env
        # var is set, surface a clear RuntimeError instead of a bare
        # ImportError so users know which package to install.
        with self.assertRaises(RuntimeError) as ctx:
            _OTelSDKConfigurator()._configure()
        self.assertIn("opentelemetry-configuration", str(ctx.exception))
        mock_init_components.assert_not_called()

    @patch.dict("os.environ", {OTEL_CONFIG_FILE: "/tmp/otel.yaml"})
    def test_env_var_set_with_kwargs_warns_and_ignores(self):
        fake = _FakeConfigurationModule()
        fake.load_config_file.return_value = object()

        with patch.dict("sys.modules", {"opentelemetry.configuration": fake}):
            with self.assertLogs(
                "opentelemetry.sdk._configuration", level="WARNING"
            ) as captured:
                _OTelSDKConfigurator()._configure(
                    sampler="X", auto_instrumentation_version="Y"
                )

        self.assertTrue(
            any(
                "OTEL_CONFIG_FILE" in msg and "sampler" in msg
                for msg in captured.output
            ),
            f"Expected warning about ignored kwargs, got: {captured.output}",
        )
        fake.configure_sdk.assert_called_once()

    @patch.dict("os.environ", {}, clear=True)
    @patch("opentelemetry.sdk._configuration._initialize_components")
    def test_distro_override_pattern_still_works(self, mock_init_components):
        class CustomConfigurator(_OTelSDKConfigurator):
            def _configure(self, **kwargs):
                kwargs["sampler"] = "TEST_SAMPLER"
                super()._configure(**kwargs)

        CustomConfigurator()._configure(auto_instrumentation_version="V")

        mock_init_components.assert_called_once_with(
            auto_instrumentation_version="V", sampler="TEST_SAMPLER"
        )
