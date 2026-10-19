# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import enum
import unittest

from opentelemetry._logs.severity import SeverityNumber


class TestSeverityNumber(unittest.TestCase):
    def test_inheritance(self):
        self.assertTrue(issubclass(SeverityNumber, enum.IntEnum))
        self.assertTrue(issubclass(SeverityNumber, int))
        self.assertIsInstance(SeverityNumber.INFO, int)

    def test_values(self):
        expected_values = {
            "UNSPECIFIED": 0,
            "TRACE": 1,
            "TRACE2": 2,
            "TRACE3": 3,
            "TRACE4": 4,
            "DEBUG": 5,
            "DEBUG2": 6,
            "DEBUG3": 7,
            "DEBUG4": 8,
            "INFO": 9,
            "INFO2": 10,
            "INFO3": 11,
            "INFO4": 12,
            "WARN": 13,
            "WARN2": 14,
            "WARN3": 15,
            "WARN4": 16,
            "ERROR": 17,
            "ERROR2": 18,
            "ERROR3": 19,
            "ERROR4": 20,
            "FATAL": 21,
            "FATAL2": 22,
            "FATAL3": 23,
            "FATAL4": 24,
        }
        for name, expected_val in expected_values.items():
            member = getattr(SeverityNumber, name)
            self.assertEqual(member.value, expected_val)
            self.assertEqual(member, expected_val)
            self.assertEqual(member.name, name)

    def test_comparisons_between_members(self):
        self.assertLess(SeverityNumber.DEBUG, SeverityNumber.INFO)
        self.assertLessEqual(SeverityNumber.INFO, SeverityNumber.WARN)
        self.assertLessEqual(SeverityNumber.INFO, SeverityNumber.INFO)
        self.assertGreater(SeverityNumber.FATAL, SeverityNumber.ERROR)
        self.assertGreaterEqual(SeverityNumber.WARN, SeverityNumber.INFO)
        self.assertGreaterEqual(SeverityNumber.WARN, SeverityNumber.WARN)
        self.assertEqual(SeverityNumber.INFO, SeverityNumber.INFO)
        self.assertNotEqual(SeverityNumber.INFO, SeverityNumber.WARN)

    def test_comparisons_with_ints(self):
        self.assertEqual(SeverityNumber.INFO, 9)
        self.assertNotEqual(SeverityNumber.INFO, 10)
        self.assertLess(SeverityNumber.DEBUG, 9)
        self.assertGreater(SeverityNumber.ERROR, 9)
        self.assertLessEqual(SeverityNumber.INFO, 9)
        self.assertGreaterEqual(SeverityNumber.INFO, 9)

    def test_sorting(self):
        severities = [
            SeverityNumber.ERROR,
            SeverityNumber.TRACE,
            SeverityNumber.FATAL,
            SeverityNumber.DEBUG,
            SeverityNumber.INFO,
        ]
        sorted_severities = sorted(severities)
        expected = [
            SeverityNumber.TRACE,
            SeverityNumber.DEBUG,
            SeverityNumber.INFO,
            SeverityNumber.ERROR,
            SeverityNumber.FATAL,
        ]
        self.assertEqual(sorted_severities, expected)

    def test_int_conversion_and_lookup(self):
        self.assertEqual(int(SeverityNumber.INFO), 9)
        self.assertIs(SeverityNumber(9), SeverityNumber.INFO)
