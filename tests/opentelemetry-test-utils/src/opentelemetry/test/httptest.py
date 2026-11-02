# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""A real HTTP server for tests of HTTP client instrumentation.

Instrumentation of an HTTP client is hard to test against a mock, because the
behaviour under test includes what the client library does with a real socket,
with keep-alive, and with an error status. :class:`HttpTestBase` starts an
actual ``http.server`` on a loopback port for the duration of the test class, so
the client under test makes a real request.
"""

import re
import unittest
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread


class HttpTestBase(unittest.TestCase):
    """Base class that runs an HTTP server for the whole test class.

    ``setUpClass`` binds a server to an ephemeral port on ``127.0.0.1`` and
    serves it from a daemon thread; ``tearDownClass`` shuts it down and joins
    that thread. The port is chosen by the operating system, so read it from
    ``cls.server.server_address[1]`` rather than assuming one.

    The server answers ``GET /`` with ``DEFAULT_RESPONSE`` and ``200``, and
    ``GET /status/<code>`` with ``<code>``, which is how a test drives the
    client under test into an error path. Every other method gets the ``501``
    that ``BaseHTTPRequestHandler`` returns for an unimplemented verb.

    Override ``Handler`` in a subclass to answer differently. ``create_server``
    reads ``cls.Handler``, so the override takes effect without touching the
    other methods. Overriding ``DEFAULT_RESPONSE`` instead does nothing:
    ``do_GET`` reads ``HttpTestBase.DEFAULT_RESPONSE`` off this class, so a
    subclass attribute of that name is never consulted and the body stays
    ``b"Hello!"``.
    """

    DEFAULT_RESPONSE = b"Hello!"

    class Handler(BaseHTTPRequestHandler):
        """Request handler answering ``/`` and ``/status/<code>``."""

        protocol_version = "HTTP/1.1"  # Support keep-alive.
        timeout = 3  # Seconds

        STATUS_RE = re.compile(r"/status/(\d+)")

        def do_GET(self):  # pylint:disable=invalid-name
            """Answer a GET request, with the status the path asks for.

            A path of the form ``/status/<code>`` is answered with that status
            and, unless it is ``200``, with the error body that
            ``send_error`` generates. Any other path is answered with ``200``
            and ``HttpTestBase.DEFAULT_RESPONSE``. The path is matched in full,
            so ``/status/404/extra`` is treated as an ordinary path and gets
            ``200``.
            """
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
        """Build a server bound to an ephemeral loopback port, without serving.

        Returns:
            An ``HTTPServer`` bound to ``127.0.0.1`` on a port the operating
            system picked, using ``cls.Handler``. It is bound but not yet
            serving, so a caller that wants requests answered has to drive
            ``serve_forever`` itself, which is what ``run_server`` does.
        """
        server_address = ("127.0.0.1", 0)  # Only bind to localhost.
        return HTTPServer(server_address, cls.Handler)

    @classmethod
    def run_server(cls):
        """Build a server and serve it from a background thread.

        Returns:
            A tuple of the worker thread and the ``HTTPServer`` it serves. The
            thread is a daemon, so it does not keep the interpreter alive, but
            shutting the server down and joining the thread is still the
            caller's job, which is what ``tearDownClass`` does.
        """
        httpd = cls.create_server()
        worker = Thread(target=httpd.serve_forever, daemon=True, name="Test server worker")
        worker.start()
        return worker, httpd

    @classmethod
    def setUpClass(cls):
        """Start the shared server and record it on the class.

        One server serves every test method of the class, so a test that wants
        the server to have seen no earlier request needs its own class.
        """
        super().setUpClass()
        cls.server_thread, cls.server = cls.run_server()

    @classmethod
    def tearDownClass(cls):
        """Stop the shared server and wait for its thread to finish.

        ``shutdown`` already blocks until the serve loop has returned, so no
        request is still being answered once it comes back and the ``join``
        only reaps a thread that has already finished. The listening socket is
        not closed here, since ``server_close`` is never called.
        """
        cls.server.shutdown()
        cls.server_thread.join()
        super().tearDownClass()
