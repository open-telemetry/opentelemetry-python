# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access

import os
import tempfile
import unittest

from opentelemetry.sdk import configuration
from opentelemetry.sdk._configuration._exceptions import ConfigurationError
from opentelemetry.sdk._configuration._sdk import configure_sdk
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
        # Public namespace re-exports the same objects for the eager binds,
        # not copies.
        self.assertIs(configuration.ConfigurationError, ConfigurationError)
        self.assertIs(
            configuration.OpenTelemetryConfiguration,
            OpenTelemetryConfiguration,
        )
        self.assertIs(configuration.configure_sdk, configure_sdk)

    def test_load_config_file_delegates_to_loader(self):
        # ``load_config_file`` is a thin wrapper that defers importing the
        # file loader until first call (so the optional ``[file-configuration]``
        # extras stay optional). Behaviourally it must round-trip a minimal
        # valid file to an ``OpenTelemetryConfiguration``.
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as fh:
            fh.write('file_format: "1.0"\n')
            path = fh.name
        try:
            result = configuration.load_config_file(path)
        finally:
            os.unlink(path)
        self.assertIsInstance(result, OpenTelemetryConfiguration)
        self.assertEqual(result.file_format, "1.0")

    def test_unknown_attribute_raises(self):
        with self.assertRaises(AttributeError):
            # pylint: disable=no-member
            _ = configuration.no_such_thing

    def test_dunder_all_is_exhaustive(self):
        self.assertEqual(sorted(configuration.__all__), list(_PUBLIC_NAMES))
