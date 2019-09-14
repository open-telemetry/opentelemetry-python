import unittest
from unittest import mock

import requests
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

import opentelemetry_example_app.flask_example as flask_example
from opentelemetry.sdk import trace
from opentelemetry.sdk.context.propagation import b3_format


class TestFlaskExample(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = flask_example.app

    def setUp(self):
        mocked_response = requests.models.Response()
        mocked_response.status_code = 200
        mocked_response.reason = "Roger that!"
        self.send_patcher = mock.patch.object(
            requests.Session,
            "send",
            autospec=True,
            spec_set=True,
            return_value=mocked_response,
        )
        self.send = self.send_patcher.start()

    def tearDown(self):
        self.send_patcher.stop()

    def test_full_path(self):
        trace_id = trace.generate_trace_id()
        # We need to use the Werkzeug test app because
        # The headers are injected at the wsgi layer.
        # The flask test app will not include these, and
        # result in the values not propagated.
        client = Client(self.app.wsgi_app, BaseResponse)
        # emulate b3 headers
        client.get(
            "/",
            headers={
                "x-b3-traceid": b3_format.format_trace_id(trace_id),
                "x-b3-spanid": b3_format.format_span_id(
                    trace.generate_span_id()
                ),
                "x-b3-sampled": "1",
            },
        )
        # assert the http request header was propagated through.
        prepared_request = self.send.call_args[0][1]
        headers = prepared_request.headers
        for required_header in {"x-b3-traceid", "x-b3-spanid", "x-b3-sampled"}:
            assert required_header in headers
        assert headers["x-b3-traceid"] == b3_format.format_trace_id(trace_id)
