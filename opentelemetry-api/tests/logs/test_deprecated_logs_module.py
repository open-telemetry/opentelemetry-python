# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access
from __future__ import annotations

import importlib
import sys
import unittest
import warnings
from unittest.mock import Mock, patch

import opentelemetry.logs
import opentelemetry.logs._internal
import opentelemetry.logs.severity

_DEPRECATED_MODULES = (
    "opentelemetry._logs",
    "opentelemetry._logs._internal",
    "opentelemetry._logs.severity",
)


def _unload_deprecated_modules() -> None:
    for name in _DEPRECATED_MODULES:
        sys.modules.pop(name, None)
    sys.modules["opentelemetry"].__dict__.pop("_logs", None)


class TestDeprecatedLogsModule(unittest.TestCase):
    def setUp(self) -> None:
        _unload_deprecated_modules()

    def test_import_emits_deprecation_warning(self) -> None:
        for name in _DEPRECATED_MODULES:
            with self.subTest(module=name):
                _unload_deprecated_modules()
                with self.assertWarns(DeprecationWarning) as context:
                    importlib.import_module(name)
                message = str(context.warning)
                self.assertIn("opentelemetry.logs", message)
                self.assertIn("will be removed in a future release", message)

    def test_deprecation_warning_points_at_importer(self) -> None:
        # pylint: disable=import-outside-toplevel,unused-import,redefined-outer-name,import-error
        # Literal import statements are required here since importlib.import_module
        # would attribute the warning to importlib itself.
        with self.subTest(statement="import opentelemetry._logs"):
            _unload_deprecated_modules()
            with self.assertWarns(DeprecationWarning) as context:
                import opentelemetry._logs  # noqa: F401, PLC0415
            self.assertEqual(context.filename, __file__)

        with self.subTest(statement="from opentelemetry._logs import ..."):
            _unload_deprecated_modules()
            with self.assertWarns(DeprecationWarning) as context:
                from opentelemetry._logs import get_logger  # noqa: F401, PLC0415
            self.assertEqual(context.filename, __file__)

        with self.subTest(statement="from opentelemetry._logs.severity import ..."):
            _unload_deprecated_modules()
            with self.assertWarns(DeprecationWarning) as context:
                from opentelemetry._logs.severity import (  # noqa: F401, PLC0415
                    SeverityNumber,
                )
            self.assertEqual(context.filename, __file__)

    def test_new_module_does_not_emit_deprecation_warning(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            importlib.reload(opentelemetry.logs)
        self.assertEqual(
            [w for w in caught if issubclass(w.category, DeprecationWarning)],
            [],
        )
        self.assertNotIn("opentelemetry._logs", sys.modules)

    def test_reexports_are_identical(self) -> None:
        with self.assertWarns(DeprecationWarning):
            deprecated = importlib.import_module("opentelemetry._logs")

        self.assertEqual(deprecated.__all__, opentelemetry.logs.__all__)
        for name in opentelemetry.logs.__all__:
            with self.subTest(name=name):
                self.assertIs(getattr(deprecated, name), getattr(opentelemetry.logs, name))

    def test_submodules_are_aliased(self) -> None:
        with self.assertWarns(DeprecationWarning):
            importlib.import_module("opentelemetry._logs")

        self.assertIs(
            importlib.import_module("opentelemetry._logs._internal"),
            opentelemetry.logs._internal,
        )
        self.assertIs(
            importlib.import_module("opentelemetry._logs.severity"),
            opentelemetry.logs.severity,
        )

    def test_patching_deprecated_path_patches_new_module(self) -> None:
        with self.assertWarns(DeprecationWarning):
            importlib.import_module("opentelemetry._logs")

        mock_load_provider = Mock()
        with patch("opentelemetry._logs._internal._load_provider", mock_load_provider):
            self.assertIs(opentelemetry.logs._internal._load_provider, mock_load_provider)
