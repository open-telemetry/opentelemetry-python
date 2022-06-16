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

import asyncio

from asgiref.testing import ApplicationCommunicator

from opentelemetry.test.test_base import TestBase


def setup_testing_defaults(scope):
    scope.update(
        {
            "client": ("127.0.0.1", 32767),
            "headers": [],
            "http_version": "1.0",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "scheme": "http",
            "server": ("127.0.0.1", 80),
            "type": "http",
        }
    )


class AsgiTestBase(TestBase):
    def setUp(self):
        super().setUp()

        self.scope = {}
        setup_testing_defaults(self.scope)
        self.communicator = None

    def tearDown(self):
        if self.communicator:
            asyncio.get_event_loop().run_until_complete(
                self.communicator.wait()
            )

    def seed_app(self, app):
        self.communicator = ApplicationCommunicator(app, self.scope)

    def send_input(self, message):
        asyncio.get_event_loop().run_until_complete(
            self.communicator.send_input(message)
        )

    def send_default_request(self):
        self.send_input({"type": "http.request", "body": b""})

    def get_output(self):
        output = asyncio.get_event_loop().run_until_complete(
            self.communicator.receive_output(0)
        )
        return output

    def get_all_output(self):
        outputs = []
        while True:
            try:
                outputs.append(self.get_output())
            except asyncio.TimeoutError:
                break
        return outputs
