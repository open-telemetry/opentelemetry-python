# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Tests access private members of SDK classes to assert correct configuration.
# pylint: disable=protected-access

import unittest
from unittest.mock import patch

from opentelemetry.sdk._configuration import _OTelSDKConfigurator
from opentelemetry.sdk._configuration._exceptions import ConfigurationError
from opentelemetry.sdk.environment_variables import OTEL_CONFIG_FILE


class TestConfiguratorFileRouting(unittest.TestCase):
    def setUp(self):
        # _BaseConfigurator caches instances via a singleton; reset so each
        # test sees a clean state and doesn't poison MRO lookups for sibling
        # tests (e.g. test_configurator.py's CustomConfigurator subclass).
        _OTelSDKConfigurator._instance = None

    def tearDown(self):
        _OTelSDKConfigurator._instance = None

    @patch.dict("os.environ", {}, clear=True)
    @patch("opentelemetry.sdk._configuration._initialize_components")
    # pylint: disable=no-self-use
    def test_env_var_unset_runs_env_var_path(self, mock_init_components):
        _OTelSDKConfigurator()._configure(auto_instrumentation_version="X")
        mock_init_components.assert_called_once_with(
            auto_instrumentation_version="X"
        )

    @patch.dict("os.environ", {OTEL_CONFIG_FILE: "/tmp/otel.yaml"})
    @patch("opentelemetry.sdk._configuration._sdk.configure_sdk")
    @patch(
        "opentelemetry.sdk._configuration.file._loader.load_config_file"
    )
    @patch("opentelemetry.sdk._configuration._initialize_components")
    # pylint: disable=no-self-use
    def test_env_var_set_routes_to_declarative_path(
        self, mock_init_components, mock_load, mock_configure_sdk
    ):
        sentinel_config = object()
        mock_load.return_value = sentinel_config

        _OTelSDKConfigurator()._configure()

        mock_load.assert_called_once_with("/tmp/otel.yaml")
        mock_configure_sdk.assert_called_once_with(sentinel_config)
        mock_init_components.assert_not_called()

    @patch.dict("os.environ", {OTEL_CONFIG_FILE: "/does/not/exist.yaml"})
    @patch("opentelemetry.sdk._configuration._initialize_components")
    # pylint: disable=no-self-use
    def test_env_var_set_missing_file_propagates(self, mock_init_components):
        with self.assertRaises(ConfigurationError):
            _OTelSDKConfigurator()._configure()
        mock_init_components.assert_not_called()

    @patch.dict("os.environ", {OTEL_CONFIG_FILE: "/tmp/otel.yaml"})
    @patch("opentelemetry.sdk._configuration._sdk.configure_sdk")
    @patch(
        "opentelemetry.sdk._configuration.file._loader.load_config_file"
    )
    def test_env_var_set_with_kwargs_warns_and_ignores(
        self, mock_load, mock_configure_sdk
    ):
        mock_load.return_value = object()

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
        mock_configure_sdk.assert_called_once()

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
