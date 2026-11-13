# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from unittest import TestCase

from opentelemetry.util._kwargs import _non_default_kwargs


class TestNonDefaultKwargs(TestCase):
    def test_drops_none_values(self):
        self.assertEqual(_non_default_kwargs(first=None, second=None), {})

    def test_keeps_set_values(self):
        self.assertEqual(
            _non_default_kwargs(first=None, second=["a"], third=1.5),
            {"second": ["a"], "third": 1.5},
        )

    def test_keeps_falsy_values(self):
        self.assertEqual(
            _non_default_kwargs(empty_list=[], zero=0, empty_str="", false=False),
            {"empty_list": [], "zero": 0, "empty_str": "", "false": False},
        )
