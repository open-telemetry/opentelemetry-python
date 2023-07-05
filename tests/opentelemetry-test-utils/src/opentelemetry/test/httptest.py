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

import re
import unittest
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread


class HttpTestBase(unittest.TestCase):
    DEFAULT_RESPONSE = b"Hello!"

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"  # Support keep-alive.
        timeout = 3  # Seconds

        STATUS_RE = re.compile(r"/status/(\d+)")

        def do_GET(self):  # pylint:disable=invalid-name
            status_match = self.STATUS_RE.fullmatch(self.path)
            status = 200
            if status_match:
                status = int(status_match.group(1))
            if status == 200:
                body = HttpTestBase.DEFAULT_RESPONSE
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_error(status)

    @classmethod
    def create_server(cls):
        server_address = ("127.0.0.1", 0)  # Only bind to localhost.
        return HTTPServer(server_address, cls.Handler)

    @classmethod
    def run_server(cls):
        httpd = cls.create_server()
        worker = Thread(
            target=httpd.serve_forever, daemon=True, name="Test server worker"
        )
        worker.start()
        return worker, httpd

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.server_thread, cls.server = cls.run_server()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server_thread.join()
        super().tearDownClass()
