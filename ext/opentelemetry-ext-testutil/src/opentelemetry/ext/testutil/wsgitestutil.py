import io
import unittest
import unittest.mock as mock
import wsgiref.util as wsgiref_util

from opentelemetry import trace as trace_api


class WsgiTestBase(unittest.TestCase):
    def setUp(self):
        self.span = mock.create_autospec(trace_api.Span, spec_set=True)
        tracer = trace_api.Tracer()
        self.get_tracer_patcher = mock.patch.object(
            trace_api.TracerSource,
            "get_tracer",
            autospec=True,
            spec_set=True,
            return_value=tracer,
        )
        self.get_tracer_patcher.start()

        self.start_span_patcher = mock.patch.object(
            tracer,
            "start_span",
            autospec=True,
            spec_set=True,
            return_value=self.span,
        )
        self.start_span = self.start_span_patcher.start()
        self.write_buffer = io.BytesIO()
        self.write = self.write_buffer.write

        self.environ = {}
        wsgiref_util.setup_testing_defaults(self.environ)

        self.status = None
        self.response_headers = None
        self.exc_info = None

    def tearDown(self):
        self.get_tracer_patcher.stop()
        self.start_span_patcher.stop()

    def start_response(self, status, response_headers, exc_info=None):
        self.status = status
        self.response_headers = response_headers
        self.exc_info = exc_info
        return self.write
