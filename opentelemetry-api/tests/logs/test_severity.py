# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest

from opentelemetry._logs import SeverityNumber


class TestSeverityNumber(unittest.TestCase):
    def test_severity_number_is_int(self):
        self.assertIsInstance(SeverityNumber.INFO, int)
        self.assertEqual(SeverityNumber.INFO, 9)
        self.assertGreater(SeverityNumber.WARN, SeverityNumber.INFO)
        self.assertIs(SeverityNumber(9), SeverityNumber.INFO)
