# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
import os
import subprocess
import sys
import unittest


class TestBasicTracerExample(unittest.TestCase):
    def test_basic_tracer(self):
        dirpath = os.path.dirname(os.path.realpath(__file__))
        test_script = f"{dirpath}/../tracing_example.py"
        output = subprocess.check_output(
            (sys.executable, test_script)
        ).decode()

        self.assertIn('"name": "foo"', output)
        self.assertIn('"name": "bar"', output)
        self.assertIn('"name": "baz"', output)
