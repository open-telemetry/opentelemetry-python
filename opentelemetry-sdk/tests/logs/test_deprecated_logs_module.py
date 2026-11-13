# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access
from __future__ import annotations

import importlib
import sys
import unittest
import warnings
from unittest.mock import Mock, patch

import opentelemetry.sdk.logs
import opentelemetry.sdk.logs._internal
import opentelemetry.sdk.logs._internal._exceptions
import opentelemetry.sdk.logs._internal._logger_metrics
import opentelemetry.sdk.logs._internal.export
import opentelemetry.sdk.logs._internal.export.in_memory_log_exporter
import opentelemetry.sdk.logs.export

_DEPRECATED_MODULES = (
    "opentelemetry.sdk._logs",
    "opentelemetry.sdk._logs.export",
    "opentelemetry.sdk._logs._internal",
    "opentelemetry.sdk._logs._internal._exceptions",
    "opentelemetry.sdk._logs._internal._logger_metrics",
    "opentelemetry.sdk._logs._internal.export",
    "opentelemetry.sdk._logs._internal.export.in_memory_log_exporter",
)


def _unload_deprecated_modules() -> None:
    for name in _DEPRECATED_MODULES:
        sys.modules.pop(name, None)
    sys.modules["opentelemetry.sdk"].__dict__.pop("_logs", None)


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
                self.assertIn("opentelemetry.sdk.logs", message)
                self.assertIn("will be removed in a future release", message)

    def test_deprecation_warning_points_at_importer(self) -> None:
        # pylint: disable=import-outside-toplevel,unused-import,redefined-outer-name,import-error
        # Literal import statements are required here since importlib.import_module
        # would attribute the warning to importlib itself.
        with self.subTest(statement="import opentelemetry.sdk._logs"):
            _unload_deprecated_modules()
            with self.assertWarns(DeprecationWarning) as context:
                import opentelemetry.sdk._logs  # noqa: F401, PLC0415
            self.assertEqual(context.filename, __file__)

        with self.subTest(statement="from opentelemetry.sdk._logs import ..."):
            _unload_deprecated_modules()
            with self.assertWarns(DeprecationWarning) as context:
                from opentelemetry.sdk._logs import LoggerProvider  # noqa: F401, PLC0415
            self.assertEqual(context.filename, __file__)

        with self.subTest(statement="from opentelemetry.sdk._logs.export import ..."):
            _unload_deprecated_modules()
            with self.assertWarns(DeprecationWarning) as context:
                from opentelemetry.sdk._logs.export import (  # noqa: F401, PLC0415
                    BatchLogRecordProcessor,
                )
            self.assertEqual(context.filename, __file__)

    def test_new_module_does_not_emit_deprecation_warning(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            importlib.reload(opentelemetry.sdk.logs)
            importlib.reload(opentelemetry.sdk.logs.export)
        self.assertEqual(
            [w for w in caught if issubclass(w.category, DeprecationWarning)],
            [],
        )
        self.assertNotIn("opentelemetry.sdk._logs", sys.modules)

    def test_reexports_are_identical(self) -> None:
        with self.assertWarns(DeprecationWarning):
            deprecated = importlib.import_module("opentelemetry.sdk._logs")

        self.assertEqual(deprecated.__all__, opentelemetry.sdk.logs.__all__)
        for name in opentelemetry.sdk.logs.__all__:
            with self.subTest(name=name):
                self.assertIs(getattr(deprecated, name), getattr(opentelemetry.sdk.logs, name))

    def test_submodules_are_aliased(self) -> None:
        with self.assertWarns(DeprecationWarning):
            importlib.import_module("opentelemetry.sdk._logs")

        aliases = {
            "opentelemetry.sdk._logs.export": opentelemetry.sdk.logs.export,
            "opentelemetry.sdk._logs._internal": opentelemetry.sdk.logs._internal,
            "opentelemetry.sdk._logs._internal._exceptions": opentelemetry.sdk.logs._internal._exceptions,
            "opentelemetry.sdk._logs._internal._logger_metrics": opentelemetry.sdk.logs._internal._logger_metrics,
            "opentelemetry.sdk._logs._internal.export": opentelemetry.sdk.logs._internal.export,
            "opentelemetry.sdk._logs._internal.export.in_memory_log_exporter": (
                opentelemetry.sdk.logs._internal.export.in_memory_log_exporter
            ),
        }
        for old_name, new_module in aliases.items():
            with self.subTest(module=old_name):
                self.assertIs(importlib.import_module(old_name), new_module)

    def test_patching_deprecated_path_patches_new_module(self) -> None:
        with self.assertWarns(DeprecationWarning):
            importlib.import_module("opentelemetry.sdk._logs")

        mock_create_logger_metrics = Mock()
        with patch(
            "opentelemetry.sdk._logs._internal.create_logger_metrics",
            mock_create_logger_metrics,
        ):
            self.assertIs(
                opentelemetry.sdk.logs._internal.create_logger_metrics,
                mock_create_logger_metrics,
            )
