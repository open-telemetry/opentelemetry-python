# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""A ``TestBase`` that supplies the WSGI environment and the ``start_response``.

A WSGI application is a callable taking an environment dict and a
``start_response`` callable, so a test of WSGI instrumentation has to supply
both and then read back what the application passed to ``start_response``.
:class:`WsgiTestBase` builds a default environment and acts as the
``start_response`` itself, recording the status, the headers and the exception
information on the test case.
"""

import io
import wsgiref.util as wsgiref_util

from opentelemetry import trace
from opentelemetry.test.test_base import TestBase


class WsgiTestBase(TestBase):
    """Base class for a test that calls a WSGI application directly.

    Inherits the in-memory trace and metrics pipelines of
    :class:`opentelemetry.test.test_base.TestBase`, so a test can assert on the
    spans the application produced as well as on the response it returned.

    ``setUp`` leaves four attributes to pass into the application and three to
    read back out of it. ``self.environ`` is the WSGI environment, filled with
    the defaults of ``wsgiref.util.setup_testing_defaults``, which describe a
    ``GET /`` over HTTP/1.0 whose only request header is ``HTTP_HOST``, set to
    ``127.0.0.1``; edit it before the call to change the request.
    ``self.start_response`` is the callable to hand to the application,
    ``self.write`` is the write callable it returns, and ``self.write_buffer``
    is the ``BytesIO`` that write callable appends to.
    After the call, ``self.status``, ``self.response_headers`` and
    ``self.exc_info`` hold what the application passed to ``start_response``,
    and stay ``None`` if it never called it.
    """

    def setUp(self):
        """Build a fresh WSGI environment and clear the recorded response.

        Every attribute is replaced rather than cleared in place, so a
        reference one test method kept does not leak into the next.
        """
        super().setUp()

        self.write_buffer = io.BytesIO()
        self.write = self.write_buffer.write

        self.environ = {}
        wsgiref_util.setup_testing_defaults(self.environ)

        self.status = None
        self.response_headers = None
        self.exc_info = None

    def start_response(self, status, response_headers, exc_info=None):
        """Record the response the application is starting, as WSGI requires.

        This is the ``start_response`` callable to pass to the application
        under test. It records its arguments rather than writing anything, and
        it does not implement the WSGI rule that a second call with
        ``exc_info`` has to re-raise, so a test of that rule needs its own
        callable.

        Args:
            status: The status line the application is sending, for example
                ``"200 OK"``.
            response_headers: The list of header name and value pairs.
            exc_info: The ``sys.exc_info()`` triple when the application is
                replacing an already-started response after an error, and
                ``None`` otherwise.

        Returns:
            The ``write`` callable of ``self.write_buffer``, which is the
            legacy WSGI write callable. An application that uses it appends to
            that buffer.
        """
        self.status = status
        self.response_headers = response_headers
        self.exc_info = exc_info
        return self.write

    def assertTraceResponseHeaderMatchesSpan(self, headers, span):  # pylint: disable=invalid-name
        """Assert that the ``traceresponse`` header identifies a given span.

        Checks that the header is present, that
        ``access-control-expose-headers`` names it so a browser can read it
        cross-origin, and that its value is the W3C Trace Context version 0
        encoding of the trace id, span id and trace flags of the span.

        Args:
            headers: The response headers, looked up by lowercase name, so a
                plain dict has to use lowercase keys.
            span: The span the header is expected to identify. Its span context
                is read, so a non-recording span with a valid context works.
        """
        self.assertIn("traceresponse", headers)
        self.assertEqual(
            headers["access-control-expose-headers"],
            "traceresponse",
        )

        trace_id = trace.format_trace_id(span.get_span_context().trace_id)
        span_id = trace.format_span_id(span.get_span_context().span_id)
        trace_flags = span.get_span_context().trace_flags
        self.assertEqual(
            f"00-{trace_id}-{span_id}-{trace_flags:02x}",
            headers["traceresponse"],
        )
