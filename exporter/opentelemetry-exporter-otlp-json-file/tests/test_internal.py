# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import unittest

from opentelemetry.exporter.otlp.json.file._internal import _format_line


class TestFormatLine(unittest.TestCase):
    def test_produces_valid_json(self):
        result = _format_line({"a": 1, "b": "hello"})
        parsed = json.loads(result.strip())
        self.assertEqual(parsed, {"a": 1, "b": "hello"})

    def test_newline_terminated(self):
        result = _format_line({"x": 0})
        self.assertTrue(result.endswith("\n"))

    def test_compact_no_spaces(self):
        result = _format_line({"a": 1, "b": 2})
        self.assertNotIn(" ", result)

    def test_nested_structure(self):
        entry = {"outer": {"inner": [1, 2, 3]}, "flag": True}
        result = _format_line(entry)
        parsed = json.loads(result.strip())
        self.assertEqual(parsed, entry)
