import io
import wsgiref.util as wsgiref_util

from opentelemetry.ext.testutil.spantestutil import SpanTestBase


class WsgiTestBase(SpanTestBase):
    def setUp(self):
        super().setUp()

        self.write_buffer = io.BytesIO()
        self.write = self.write_buffer.write

        self.environ = {}
        wsgiref_util.setup_testing_defaults(self.environ)

        self.status = None
        self.response_headers = None
        self.exc_info = None

    def start_response(self, status, response_headers, exc_info=None):
        self.status = status
        self.response_headers = response_headers
        self.exc_info = exc_info
        return self.write
