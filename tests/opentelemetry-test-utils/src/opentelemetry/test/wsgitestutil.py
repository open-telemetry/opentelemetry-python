# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import io
import wsgiref.util as wsgiref_util

from opentelemetry import trace
from opentelemetry.test.test_base import TestBase


class WsgiTestBase(TestBase):
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

    def assertTraceResponseHeaderMatchesSpan(self, headers, span):  # pylint: disable=invalid-name
        self.assertIn("traceresponse", headers)
        self.assertEqual(
            headers["access-control-expose-headers"],
            "traceresponse",
        )

        trace_id = trace.format_trace_id(span.get_span_context().trace_id)
        span_id = trace.format_span_id(span.get_span_context().span_id)
        self.assertEqual(
            f"00-{trace_id}-{span_id}-01",
            headers["traceresponse"],
        )
