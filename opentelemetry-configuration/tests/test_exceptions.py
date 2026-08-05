# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest

from opentelemetry.configuration._exceptions import (
    ConfigurationError,
    MissingDependencyError,
)


class TestMissingDependencyError(unittest.TestCase):
    def test_is_configuration_error_subclass(self):
        self.assertTrue(issubclass(MissingDependencyError, ConfigurationError))

    def test_minimal_constructor(self):
        exc = MissingDependencyError(package="foo")
        self.assertEqual(exc.package, "foo")
        self.assertIsNone(exc.feature)
        self.assertEqual(exc.install_name, "foo")
        self.assertIsNone(exc.extras)
        self.assertIn("'foo'", str(exc))
        self.assertIn("pip install foo", str(exc))

    def test_with_feature(self):
        exc = MissingDependencyError(package="bar", feature="Baz exporter")
        self.assertEqual(exc.package, "bar")
        self.assertEqual(exc.feature, "Baz exporter")
        self.assertIn("Baz exporter requires 'bar'", str(exc))
        self.assertIn("pip install bar", str(exc))

    def test_with_custom_install_name(self):
        exc = MissingDependencyError(
            package="pyyaml",
            install_name="opentelemetry-sdk",
            extras="file-configuration",
        )
        self.assertEqual(exc.install_name, "opentelemetry-sdk")
        self.assertEqual(exc.extras, "file-configuration")
        self.assertIn(
            'pip install "opentelemetry-sdk[file-configuration]"', str(exc)
        )

    def test_with_feature_and_extras(self):
        exc = MissingDependencyError(
            package="jsonschema",
            feature="File configuration",
            install_name="opentelemetry-sdk",
            extras="file-configuration",
        )
        self.assertIn("File configuration requires 'jsonschema'", str(exc))
        self.assertIn(
            'pip install "opentelemetry-sdk[file-configuration]"', str(exc)
        )

    def test_can_be_caught_as_configuration_error(self):
        with self.assertRaises(ConfigurationError):
            raise MissingDependencyError(package="test")

    def test_can_be_caught_as_exception(self):
        with self.assertRaises(Exception):
            raise MissingDependencyError(package="test")

    def test_can_be_caught_as_import_error(self):
        with self.assertRaises(ImportError):
            raise MissingDependencyError(package="test")

    def test_is_import_error_subclass(self):
        self.assertTrue(issubclass(MissingDependencyError, ImportError))

    def test_issubclass_import_error(self):
        self.assertIsInstance(
            MissingDependencyError(package="test"), ImportError
        )
