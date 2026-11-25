# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import gc
import multiprocessing
import os
import threading
import unittest
import warnings
import weakref
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import requests

# pylint: disable-next=import-error
from opentelemetry.exporter.http.transport._requests import (
    RequestsHTTPTransport,
)

# pylint: disable-next=import-error
from opentelemetry.exporter.http.transport._urllib3 import (
    Urllib3HTTPTransport,
)

_PROXY_TEST_URL = "http://example.test/v1/traces"


class _RecordingHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):  # pylint: disable=invalid-name
        length = int(self.headers.get("Content-Length", "0"))
        if length:
            self.rfile.read(length)
        self.server.requests_seen.append((self.client_address[1], self.headers.get("x-test")))
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format, *args):  # pylint: disable=redefined-builtin
        pass


def _request_in_child(transport, url, conn):
    conn.send(transport.request("POST", url, data=b"child").status_code)
    conn.close()


@unittest.skipUnless(
    hasattr(os, "fork") and hasattr(os, "register_at_fork"),
    "needs fork and register_at_fork",
)
class TestTransportFork(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _RecordingHandler)
        self.server.daemon_threads = True
        self.server.requests_seen = []
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/v1/traces"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def _request_in_parent_then_child(self, transport):
        self.addCleanup(transport.close)
        self.assertEqual(transport.request("POST", self.url, data=b"parent").status_code, 200)

        parent_conn, child_conn = multiprocessing.Pipe()
        with warnings.catch_warnings():
            # The server thread makes fork() warn about a multi-threaded process.
            warnings.simplefilter("ignore", DeprecationWarning)
            process = multiprocessing.get_context("fork").Process(
                target=_request_in_child, args=(transport, self.url, child_conn)
            )
            process.start()
        self.addCleanup(process.kill)
        child_conn.close()
        self.assertTrue(parent_conn.poll(10))
        self.assertEqual(parent_conn.recv(), 200)
        process.join(10)
        self.assertEqual(process.exitcode, 0)
        return self.server.requests_seen

    def test_requests_transport_does_not_reuse_parent_connection_in_child(self):
        session = requests.Session()
        session.headers["x-test"] = "custom-session"
        seen = self._request_in_parent_then_child(RequestsHTTPTransport(session=session))

        self.assertEqual(len(seen), 2)
        parent_port, child_port = seen[0][0], seen[1][0]
        self.assertNotEqual(parent_port, child_port)
        # The session passed in, with its configuration, is still used.
        self.assertEqual(seen[1][1], "custom-session")

    def test_urllib3_transport_does_not_reuse_parent_connection_in_child(self):
        seen = self._request_in_parent_then_child(Urllib3HTTPTransport())

        self.assertEqual(len(seen), 2)
        parent_port, child_port = seen[0][0], seen[1][0]
        self.assertNotEqual(parent_port, child_port)

    @patch.dict(os.environ, {"HTTP_PROXY": "http://proxy.test:3128"}, clear=True)
    def test_urllib3_fork_hook_clears_proxy_managers(self):
        with (
            patch("os.register_at_fork") as register_at_fork,
            patch("urllib3.proxy_from_url") as mock_proxy_from_url,
        ):
            transport = Urllib3HTTPTransport()
            transport.request("POST", _PROXY_TEST_URL)
        register_at_fork.call_args.kwargs["after_in_child"]()

        mock_proxy_from_url.return_value.clear.assert_called_once()
        # The proxy manager is kept for the child's next request.
        # pylint: disable-next=protected-access
        manager = transport._get_pool_manager(_PROXY_TEST_URL)
        self.assertIs(manager, mock_proxy_from_url.return_value)

    def test_fork_hook_does_not_keep_transport_alive(self):
        for transport_class in (RequestsHTTPTransport, Urllib3HTTPTransport):
            with self.subTest(transport_class.__name__):
                with patch("os.register_at_fork") as register_at_fork:
                    transport = transport_class()
                after_in_child = register_at_fork.call_args.kwargs["after_in_child"]
                transport_ref = weakref.ref(transport)
                del transport
                gc.collect()

                self.assertIsNone(transport_ref())
                after_in_child()
