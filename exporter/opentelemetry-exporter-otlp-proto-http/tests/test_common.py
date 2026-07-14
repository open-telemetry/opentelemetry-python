# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest
from unittest.mock import patch

from opentelemetry.exporter.otlp.proto.http._common import _resolve_insecure


class TestResolveInsecure(unittest.TestCase):
    def test_constructor_true_returns_true(self):
        result = _resolve_insecure(True, "SIGNAL_VAR", "GENERIC_VAR")
        self.assertTrue(result)

    def test_constructor_false_returns_false(self):
        result = _resolve_insecure(False, "SIGNAL_VAR", "GENERIC_VAR")
        self.assertFalse(result)

    def test_constructor_none_no_env_returns_false(self):
        result = _resolve_insecure(None, "SIGNAL_VAR", "GENERIC_VAR")
        self.assertFalse(result)

    @patch.dict("os.environ", {"MY_SIGNAL_INSECURE": "true"})
    def test_signal_env_var_true(self):
        result = _resolve_insecure(None, "MY_SIGNAL_INSECURE", "MY_GENERIC_INSECURE")
        self.assertTrue(result)

    @patch.dict("os.environ", {"MY_SIGNAL_INSECURE": "false"})
    def test_signal_env_var_false(self):
        result = _resolve_insecure(None, "MY_SIGNAL_INSECURE", "MY_GENERIC_INSECURE")
        self.assertFalse(result)

    @patch.dict("os.environ", {"MY_GENERIC_INSECURE": "true"})
    def test_generic_env_var_true(self):
        result = _resolve_insecure(None, "MY_SIGNAL_INSECURE", "MY_GENERIC_INSECURE")
        self.assertTrue(result)

    @patch.dict(
        "os.environ",
        {"MY_SIGNAL_INSECURE": "false", "MY_GENERIC_INSECURE": "true"},
    )
    def test_signal_env_var_takes_priority(self):
        result = _resolve_insecure(None, "MY_SIGNAL_INSECURE", "MY_GENERIC_INSECURE")
        self.assertFalse(result)

    @patch.dict("os.environ", {"MY_SIGNAL_INSECURE": "true"})
    def test_constructor_overrides_env_var(self):
        result = _resolve_insecure(False, "MY_SIGNAL_INSECURE", "MY_GENERIC_INSECURE")
        self.assertFalse(result)

    @patch.dict("os.environ", {"MY_SIGNAL_INSECURE": "TRUE"})
    def test_env_var_case_insensitive(self):
        result = _resolve_insecure(None, "MY_SIGNAL_INSECURE", "MY_GENERIC_INSECURE")
        self.assertTrue(result)

    @patch.dict("os.environ", {"MY_SIGNAL_INSECURE": "  True  "})
    def test_env_var_strips_whitespace(self):
        result = _resolve_insecure(None, "MY_SIGNAL_INSECURE", "MY_GENERIC_INSECURE")
        self.assertTrue(result)

    @patch.dict("os.environ", {"MY_SIGNAL_INSECURE": "yes"})
    def test_env_var_non_true_value_is_false(self):
        result = _resolve_insecure(None, "MY_SIGNAL_INSECURE", "MY_GENERIC_INSECURE")
        self.assertFalse(result)

    @patch.dict("os.environ", {"MY_SIGNAL_INSECURE": ""})
    def test_empty_signal_env_var_falls_through_to_generic(self):
        result = _resolve_insecure(None, "MY_SIGNAL_INSECURE", "MY_GENERIC_INSECURE")
        self.assertFalse(result)

    @patch.dict(
        "os.environ",
        {"MY_SIGNAL_INSECURE": "", "MY_GENERIC_INSECURE": "true"},
    )
    def test_empty_signal_env_falls_through_to_generic_true(self):
        result = _resolve_insecure(None, "MY_SIGNAL_INSECURE", "MY_GENERIC_INSECURE")
        self.assertTrue(result)
