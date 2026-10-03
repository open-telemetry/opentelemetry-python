# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import importlib
import sys
import unittest
from importlib.metadata import EntryPoint

import opentelemetry.exporter.otlp.json.common.log_encoder

_DEPRECATED_MODULE = "opentelemetry.exporter.otlp.json.common._log_encoder"


def _unload_deprecated_module() -> None:
    sys.modules.pop(_DEPRECATED_MODULE, None)
    sys.modules["opentelemetry.exporter.otlp.json.common"].__dict__.pop("_log_encoder", None)


class TestDeprecatedLogModule(unittest.TestCase):
    def setUp(self) -> None:
        _unload_deprecated_module()

    def test_import_emits_deprecation_warning(self) -> None:
        with self.assertWarns(DeprecationWarning) as context:
            importlib.import_module(_DEPRECATED_MODULE)
        message = str(context.warning)
        self.assertIn("opentelemetry.exporter.otlp.json.common.log_encoder", message)
        self.assertIn("will be removed in a future release", message)

    def test_deprecation_warning_points_at_importer(self) -> None:
        # pylint: disable=import-outside-toplevel,unused-import
        # A literal import statement is required here since importlib.import_module
        # would attribute the warning to importlib itself.
        with self.assertWarns(DeprecationWarning) as context:
            from opentelemetry.exporter.otlp.json.common._log_encoder import encode_logs  # noqa: F401, PLC0415
        self.assertEqual(context.filename, __file__)

    def test_reexports_are_identical(self) -> None:
        with self.assertWarns(DeprecationWarning):
            deprecated = importlib.import_module(_DEPRECATED_MODULE)

        self.assertEqual(deprecated.__all__, ["encode_logs"])
        for name in deprecated.__all__:
            with self.subTest(name=name):
                self.assertIs(
                    getattr(deprecated, name), getattr(opentelemetry.exporter.otlp.json.common.log_encoder, name)
                )

    def test_old_entry_point_target_resolves(self) -> None:
        # Entry points and configuration may still reference the old module path.
        entry_point = EntryPoint(
            name="log_encoder", value="opentelemetry.exporter.otlp.json.common._log_encoder:encode_logs", group="test"
        )
        with self.assertWarns(DeprecationWarning):
            target = entry_point.load()
        self.assertIs(target, opentelemetry.exporter.otlp.json.common.log_encoder.encode_logs)
