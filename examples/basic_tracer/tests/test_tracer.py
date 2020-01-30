# Copyright 2019, OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import subprocess
import sys
import unittest


class TestBasicTracerExample(unittest.TestCase):
    def test_basic_tracer(self):
        dirpath = os.path.dirname(os.path.realpath(__file__))
        test_script = "{}/../tracer.py".format(dirpath)
        output = subprocess.check_output(
            (sys.executable, test_script)
        ).decode()

        self.assertIn('name="foo"', output)
        self.assertIn('name="bar"', output)
        self.assertIn('name="baz"', output)
