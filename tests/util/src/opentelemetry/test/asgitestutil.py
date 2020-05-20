import asyncio

from asgiref.testing import ApplicationCommunicator

from opentelemetry.test.spantestutil import SpanTestBase


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


class AsgiTestBase(SpanTestBase):
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

    def send_input(self, payload):
        asyncio.get_event_loop().run_until_complete(
            self.communicator.send_input(payload)
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
