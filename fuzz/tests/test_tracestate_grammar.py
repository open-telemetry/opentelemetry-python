# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest

from fuzz_tracestate import (
    _MAX_KEYS,
    _MAX_LENGTH,
    _expected_entries,
    _valid_tracestates,
)
from hypothesis import HealthCheck, given, settings


def _members(count: int) -> str:
    return ",".join(f"k{index}=v" for index in range(count))


class TestTraceStateGrammar(unittest.TestCase):
    def test_valid(self):
        cases = [
            ("", []),
            (" \t", []),
            (",, ,", []),
            ("a=1", [("a", "1")]),
            (" a=1 , ,b=2 ,", [("a", "1"), ("b", "2")]),
            ("a=1\t,\tb=2", [("a", "1"), ("b", "2")]),
            ("a= b c", [("a", " b c")]),
            ("0t@s=x", [("0t@s", "x")]),
            ("a" * 256 + "=1", [("a" * 256, "1")]),
            ("t" * 241 + "@" + "s" * 14 + "=1", [("t" * 241 + "@" + "s" * 14, "1")]),
            ("a=" + "v" * 256, [("a", "v" * 256)]),
        ]
        for tracestate, entries in cases:
            with self.subTest(tracestate=tracestate):
                self.assertEqual(_expected_entries([tracestate]), entries)

    def test_invalid(self):
        cases = [
            "a =1",
            "a= ",
            "a=",
            "=1",
            "A=1",
            "0a=1",
            "a@@b=1",
            "a=1=2",
            "a=1 b=2",
            "a=\x00",
            "a=é",
            "a" * 257 + "=1",
            "t" * 242 + "@s=1",
            "t@" + "s" * 15 + "=1",
            "a=" + "v" * 257,
            "a=1,a=2",
        ]
        for tracestate in cases:
            with self.subTest(tracestate=tracestate):
                self.assertEqual(_expected_entries([tracestate]), [])

    def test_key_count(self):
        self.assertEqual(len(_expected_entries([_members(_MAX_KEYS)])), _MAX_KEYS)
        self.assertEqual(_expected_entries([_members(_MAX_KEYS + 1)]), [])

    def test_empty_members_do_not_count(self):
        tracestate = ",,".join(f"k{index}=v" for index in range(_MAX_KEYS))
        self.assertEqual(len(_expected_entries([f", {tracestate}, ,"])), _MAX_KEYS)

    def test_total_length(self):
        for padding, expected in ((_MAX_LENGTH - 3, [("a", "1")]), (_MAX_LENGTH - 2, [])):
            with self.subTest(padding=padding):
                self.assertEqual(_expected_entries(["a=1", "," * (padding - 1)]), expected)

    def test_multiple_headers(self):
        self.assertEqual(_expected_entries(["a=1", " b=2 "]), [("a", "1"), ("b", "2")])
        self.assertEqual(_expected_entries(["a=1", "a=2"]), [])

    @settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(_valid_tracestates())
    def test_generated_are_valid(self, tracestate: str):
        entries = _expected_entries([tracestate])
        self.assertEqual(len(entries), tracestate.count("="))
        self.assertLessEqual(len(entries), _MAX_KEYS)
