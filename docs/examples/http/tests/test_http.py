# Copyright The OpenTelemetry Authors
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
from time import sleep


class TestHttpExample(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        dirpath = os.path.dirname(os.path.realpath(__file__))
        server_script = "{}/../server.py".format(dirpath)
        cls.server = subprocess.Popen([sys.executable, server_script])
        sleep(1)

    def test_http(self):
        dirpath = os.path.dirname(os.path.realpath(__file__))
        test_script = "{}/../client.py".format(dirpath)
        output = subprocess.check_output(
            (sys.executable, test_script)
        ).decode()
        self.assertIn('name="/"', output)

    @classmethod
    def teardown_class(cls):
        cls.server.terminate()
