# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# oltpcollector_example.py
import os
import subprocess
import sys
import unittest


class TestOTLPCollector(unittest.TestCase):
    def test_otlpcollector(self):
        """Test that OTLP collector example outputs 'Hello world!'"""
        dirpath = os.path.dirname(os.path.realpath(__file__))
        test_script = f"{dirpath}/../otlpcollector_example.py"

        # Run the script with a short timeout since it will retry forever
        with subprocess.Popen(
            [sys.executable, test_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ) as process:
            # Wait 2 seconds then kill it (enough time to print "Hello world!")
            try:
                stdout, _ = process.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, _ = process.communicate()

        # Check that it printed the expected message
        self.assertIn("Hello world!", stdout)
