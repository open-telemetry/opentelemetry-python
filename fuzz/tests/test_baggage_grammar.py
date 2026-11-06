# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest

from fuzz_baggage import (
    _MAX_LENGTH,
    _MAX_PAIR_LENGTH,
    _MAX_PAIRS,
    _expected_entries,
    _parse_member,
    _valid_baggage,
)
from hypothesis import HealthCheck, given, settings


def _members(count: int) -> str:
    return ",".join(f"k{index}=v" for index in range(count))


class TestBaggageGrammar(unittest.TestCase):
    def test_valid(self):
        cases = [
            ("", {}),
            (" \t", {}),
            (",, ,", {}),
            ("k=v", {"k": "v"}),
            (" k = v , ,l=w ,", {"k": "v", "l": "w"}),
            ("k=", {"k": ""}),
            ("k==v", {"k": "=v"}),
            ("k=v;p", {"k": "v"}),
            ("k= ;p", {"k": ""}),
            ("k=v ; p = 1 ;q", {"k": "v"}),
            ("k=v;p=", {"k": "v"}),
            ("a!#$%&'*+-.^_`|~=1", {"a!#$%&'*+-.^_`|~": "1"}),
            ("k=%20x%41", {"k": " xA"}),
            ("k=%C3%A9", {"k": "é"}),
            ("k=%FF", {"k": "�"}),
            ("k=%zz%4", {"k": "%zz%4"}),
            ("k=" + "v" * (_MAX_PAIR_LENGTH - 2), {"k": "v" * (_MAX_PAIR_LENGTH - 2)}),
        ]
        for baggage_string, entries in cases:
            with self.subTest(baggage_string=baggage_string):
                self.assertEqual(_expected_entries([baggage_string]), entries)

    def test_invalid(self):
        cases = [
            "k",
            "=v",
            "k v=1",
            "k=v w",
            'k="v"',
            "k=a\\b",
            "k=v;",
            "k=v;;p",
            "k=v;=p",
            "k=v;p q",
            "k=v;p=v w",
            "k=é",
            "k=v;p=é",
            "k=\x00",
        ]
        for member in cases:
            with self.subTest(member=member):
                self.assertIsNone(_parse_member(member))
                self.assertEqual(_expected_entries([f"a=1,{member},b=2"]), {"a": "1", "b": "2"})

    def test_pair_length(self):
        member = "k=" + "v" * (_MAX_PAIR_LENGTH - 1)
        self.assertIsNotNone(_parse_member(member))
        self.assertEqual(_expected_entries([f"a=1,{member},b=2"]), {"a": "1", "b": "2"})

    def test_duplicate_keys(self):
        self.assertEqual(_expected_entries(["k=1,l=2,k=3"]), {"k": "3", "l": "2"})

    def test_pair_count(self):
        self.assertEqual(len(_expected_entries([_members(_MAX_PAIRS)])), _MAX_PAIRS)
        self.assertEqual(len(_expected_entries([_members(_MAX_PAIRS + 1)])), _MAX_PAIRS)

    def test_invalid_members_count(self):
        self.assertEqual(_expected_entries(["x," * _MAX_PAIRS + "k=v"]), {})
        self.assertEqual(_expected_entries([",é," * _MAX_PAIRS + "k=v"]), {"k": "v"})

    def test_total_length(self):
        first = "a=" + "x" * (_MAX_PAIR_LENGTH - 2)
        for length, expected in ((_MAX_LENGTH - len(first) - 1, 2), (_MAX_LENGTH - len(first), 1)):
            with self.subTest(length=length):
                second = "b=" + "y" * (length - 2)
                self.assertEqual(len(_expected_entries([first, second])), expected)

    def test_multiple_headers(self):
        self.assertEqual(_expected_entries(["a=1", " b=2 ", "a=3"]), {"a": "3", "b": "2"})

    @settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(_valid_baggage())
    def test_generated_are_valid(self, baggage_string: str):
        members = [member.strip(" \t") for member in baggage_string.split(",")]
        invalid = [member for member in members if member and _parse_member(member) is None]
        self.assertEqual(invalid, [])
