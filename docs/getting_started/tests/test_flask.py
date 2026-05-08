# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
import os
import subprocess
import sys
import unittest
from time import sleep

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import (  # pylint: disable=import-error
    Retry,
)


class TestFlask(unittest.TestCase):
    def test_flask(self):
        dirpath = os.path.dirname(os.path.realpath(__file__))
        server_script = f"{dirpath}/../flask_example.py"
        server = subprocess.Popen(  # pylint: disable=consider-using-with
            [sys.executable, server_script],
            stdout=subprocess.PIPE,
        )
        retry_strategy = Retry(total=10, backoff_factor=1)
        adapter = HTTPAdapter(max_retries=retry_strategy)
        http = requests.Session()
        http.mount("http://", adapter)

        try:
            result = http.get("http://localhost:5000")
            self.assertEqual(result.status_code, 200)

            sleep(5)
        finally:
            server.terminate()

        output = str(server.stdout.read())
        self.assertIn('"name": "GET"', output)
        self.assertIn('"name": "example-request"', output)
        self.assertIn('"name": "GET /"', output)
