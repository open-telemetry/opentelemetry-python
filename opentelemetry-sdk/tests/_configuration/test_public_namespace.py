# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access

import unittest

from opentelemetry.sdk import configuration
from opentelemetry.sdk._configuration._exceptions import ConfigurationError
from opentelemetry.sdk._configuration._sdk import configure_sdk
from opentelemetry.sdk._configuration.file._loader import load_config_file
from opentelemetry.sdk._configuration.models import (
    OpenTelemetryConfiguration,
)

_PUBLIC_NAMES = (
    "ConfigurationError",
    "OpenTelemetryConfiguration",
    "configure_sdk",
    "load_config_file",
)


class TestPublicNamespace(unittest.TestCase):
    def test_public_symbols_resolve(self):
        for name in _PUBLIC_NAMES:
            self.assertTrue(
                hasattr(configuration, name),
                f"{name!r} missing from public namespace",
            )

    def test_public_symbols_match_private(self):
        # Public namespace re-exports the same objects, not copies.
        self.assertIs(configuration.ConfigurationError, ConfigurationError)
        self.assertIs(
            configuration.OpenTelemetryConfiguration,
            OpenTelemetryConfiguration,
        )
        self.assertIs(configuration.configure_sdk, configure_sdk)
        self.assertIs(configuration.load_config_file, load_config_file)

    def test_unknown_attribute_raises(self):
        with self.assertRaises(AttributeError):
            _ = configuration.no_such_thing

    def test_dunder_all_is_exhaustive(self):
        self.assertEqual(sorted(configuration.__all__), list(_PUBLIC_NAMES))
