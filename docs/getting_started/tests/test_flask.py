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

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


class TestFlask(unittest.TestCase):
    def test_flask(self):
        dirpath = os.path.dirname(os.path.realpath(__file__))
        server_script = "{}/../flask_example.py".format(dirpath)
        server = subprocess.Popen(
            [sys.executable, server_script], stdout=subprocess.PIPE,
        )
        retry_strategy = Retry(total=10, backoff_factor=1)
        adapter = HTTPAdapter(max_retries=retry_strategy)
        http = requests.Session()
        http.mount("http://", adapter)

        try:
            result = http.get("http://localhost:5000")
            self.assertEqual(result.status_code, 200)

            sleep(0.1)
        finally:
            server.terminate()

        output = str(server.stdout.read())
        self.assertIn('"name": "HTTP GET"', output)
        self.assertIn('"name": "example-request"', output)
        self.assertIn('"name": "hello"', output)
