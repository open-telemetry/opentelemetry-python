# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import importlib
import sys
import unittest
from importlib.metadata import EntryPoint

import opentelemetry.exporter.otlp.json.http.log_exporter

_DEPRECATED_MODULE = "opentelemetry.exporter.otlp.json.http._log_exporter"


def _unload_deprecated_module() -> None:
    sys.modules.pop(_DEPRECATED_MODULE, None)
    sys.modules["opentelemetry.exporter.otlp.json.http"].__dict__.pop("_log_exporter", None)


class TestDeprecatedLogModule(unittest.TestCase):
    def setUp(self) -> None:
        _unload_deprecated_module()

    def test_import_emits_deprecation_warning(self) -> None:
        with self.assertWarns(DeprecationWarning) as context:
            importlib.import_module(_DEPRECATED_MODULE)
        message = str(context.warning)
        self.assertIn("opentelemetry.exporter.otlp.json.http.log_exporter", message)
        self.assertIn("will be removed in a future release", message)

    def test_deprecation_warning_points_at_importer(self) -> None:
        # pylint: disable=import-outside-toplevel,unused-import
        # A literal import statement is required here since importlib.import_module
        # would attribute the warning to importlib itself.
        with self.assertWarns(DeprecationWarning) as context:
            from opentelemetry.exporter.otlp.json.http._log_exporter import OTLPLogExporter  # noqa: F401, PLC0415
        self.assertEqual(context.filename, __file__)

    def test_reexports_are_identical(self) -> None:
        with self.assertWarns(DeprecationWarning):
            deprecated = importlib.import_module(_DEPRECATED_MODULE)

        self.assertEqual(deprecated.__all__, ["OTLPLogExporter"])
        for name in deprecated.__all__:
            with self.subTest(name=name):
                self.assertIs(
                    getattr(deprecated, name), getattr(opentelemetry.exporter.otlp.json.http.log_exporter, name)
                )

    def test_old_entry_point_target_resolves(self) -> None:
        # Entry points and configuration may still reference the old module path.
        entry_point = EntryPoint(
            name="log_exporter",
            value="opentelemetry.exporter.otlp.json.http._log_exporter:OTLPLogExporter",
            group="test",
        )
        with self.assertWarns(DeprecationWarning):
            target = entry_point.load()
        self.assertIs(target, opentelemetry.exporter.otlp.json.http.log_exporter.OTLPLogExporter)
