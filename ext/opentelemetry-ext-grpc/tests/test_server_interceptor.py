# Copyright 2020, OpenTelemetry Authors
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

import threading
import unittest
from concurrent import futures
from contextlib import contextmanager
from unittest import mock
from unittest.mock import patch

import grpc

from opentelemetry import context, trace
from opentelemetry.context.threadlocal_context import ThreadLocalRuntimeContext
from opentelemetry.ext.grpc import server_interceptor
from opentelemetry.ext.grpc.grpcext import intercept_server
from opentelemetry.sdk import trace as trace_sdk


class UnaryUnaryMethodHandler(grpc.RpcMethodHandler):
    def __init__(self, handler):
        self.request_streaming = False
        self.response_streaming = False
        self.request_deserializer = None
        self.response_serializer = None
        self.unary_unary = handler
        self.unary_stream = None
        self.stream_unary = None
        self.stream_stream = None


# lifted from
# https://github.com/grpc/grpc/blob/694f491e06b3503952ca5053c98493cf48af43c1/src/python/grpcio_tests/tests/unit/_interceptor_test.py


_SERIALIZE_REQUEST = lambda bytestring: bytestring * 2
_DESERIALIZE_REQUEST = lambda bytestring: bytestring[len(bytestring) // 2 :]
_SERIALIZE_RESPONSE = lambda bytestring: bytestring * 3
_DESERIALIZE_RESPONSE = lambda bytestring: bytestring[: len(bytestring) // 3]


_UNARY_UNARY = "/test/UnaryUnary"
_UNARY_STREAM = "/test/UnaryStream"
_STREAM_UNARY = "/test/StreamUnary"
_STREAM_STREAM = "/test/StreamStream"


class UnaryUnaryRpcHandler(grpc.GenericRpcHandler):
    def __init__(self, handler):
        self._unary_unary_handler = handler

    def service(self, handler_call_details):
        return UnaryUnaryMethodHandler(self._unary_unary_handler)


class _Handler(object):
    def __init__(self, control):
        self._control = control

    def handle_unary_unary(self, request, servicer_context):
        self._control.control()
        if servicer_context is not None:
            servicer_context.set_trailing_metadata((("testkey", "testvalue"),))
        if request == _EXCEPTION_REQUEST:
            raise _ApplicationErrorStandin()
        return request

    def handle_unary_stream(self, request, servicer_context):
        if request == _EXCEPTION_REQUEST:
            raise _ApplicationErrorStandin()
        for _ in range(test_constants.STREAM_LENGTH):
            self._control.control()
            yield request
        self._control.control()
        if servicer_context is not None:
            servicer_context.set_trailing_metadata((("testkey", "testvalue"),))

    def handle_stream_unary(self, request_iterator, servicer_context):
        if servicer_context is not None:
            servicer_context.invocation_metadata()
        self._control.control()
        response_elements = []
        for request in request_iterator:
            self._control.control()
            response_elements.append(request)
        self._control.control()
        if servicer_context is not None:
            servicer_context.set_trailing_metadata((("testkey", "testvalue"),))
        if _EXCEPTION_REQUEST in response_elements:
            raise _ApplicationErrorStandin()
        return b"".join(response_elements)

    def handle_stream_stream(self, request_iterator, servicer_context):
        self._control.control()
        if servicer_context is not None:
            servicer_context.set_trailing_metadata((("testkey", "testvalue"),))
        for request in request_iterator:
            if request == _EXCEPTION_REQUEST:
                raise _ApplicationErrorStandin()
            self._control.control()
            yield request
        self._control.control()


class _MethodHandler(grpc.RpcMethodHandler):
    def __init__(
        self,
        request_streaming,
        response_streaming,
        request_deserializer,
        response_serializer,
        unary_unary,
        unary_stream,
        stream_unary,
        stream_stream,
    ):
        self.request_streaming = request_streaming
        self.response_streaming = response_streaming
        self.request_deserializer = request_deserializer
        self.response_serializer = response_serializer
        self.unary_unary = unary_unary
        self.unary_stream = unary_stream
        self.stream_unary = stream_unary
        self.stream_stream = stream_stream


class _GenericHandler(grpc.GenericRpcHandler):
    def __init__(self, handler):
        self._handler = handler

    def service(self, handler_call_details):
        if handler_call_details.method == _UNARY_UNARY:
            return _MethodHandler(
                False,
                False,
                None,
                None,
                self._handler.handle_unary_unary,
                None,
                None,
                None,
            )
        elif handler_call_details.method == _UNARY_STREAM:
            return _MethodHandler(
                False,
                True,
                _DESERIALIZE_REQUEST,
                _SERIALIZE_RESPONSE,
                None,
                self._handler.handle_unary_stream,
                None,
                None,
            )
        elif handler_call_details.method == _STREAM_UNARY:
            return _MethodHandler(
                True,
                False,
                _DESERIALIZE_REQUEST,
                _SERIALIZE_RESPONSE,
                None,
                None,
                self._handler.handle_stream_unary,
                None,
            )
        elif handler_call_details.method == _STREAM_STREAM:
            return _MethodHandler(
                True,
                True,
                None,
                None,
                None,
                None,
                None,
                self._handler.handle_stream_stream,
            )
        else:
            return None


class TestOpenTelemetryServerInterceptor(unittest.TestCase):

    # FIXME: test_concurrent_server_spans fails with contextvars context.
    def setUp(self) -> None:
        super(TestOpenTelemetryServerInterceptor, self).setUp()
        self.mock_runtime = patch.object(
            context, "_RUNTIME_CONTEXT", ThreadLocalRuntimeContext()
        )
        self.mock_runtime.start()

    def tearDown(self) -> None:
        super(TestOpenTelemetryServerInterceptor, self).tearDown()
        self.mock_runtime.stop()

    def test_create_span(self):
        """Check that the interceptor wraps calls with spans server-side."""

        @contextmanager
        def mock_start_as_current_span(*args, **kwargs):
            yield mock.Mock(spec=trace.Span)

        # Intercept gRPC calls...
        tracer = mock.Mock(spec=trace.Tracer)
        tracer.start_as_current_span.side_effect = mock_start_as_current_span
        interceptor = server_interceptor(tracer)

        # No-op RPC handler
        def handler(request, context):
            return b""

        server = grpc.server(
            futures.ThreadPoolExecutor(), options=(("grpc.so_reuseport", 0),)
        )
        # FIXME: grpcext interceptor doesn't apply to handlers passed to server
        # init, should use intercept_service API instead.
        server = intercept_server(server, interceptor)
        server.add_generic_rpc_handlers((UnaryUnaryRpcHandler(handler),))

        port = server.add_insecure_port("[::]:0")
        channel = grpc.insecure_channel("localhost:{:d}".format(port))

        try:
            server.start()
            channel.unary_unary("")(b"")
        finally:
            server.stop(None)

        tracer.start_as_current_span.assert_called_once_with(
            name="", kind=trace.SpanKind.SERVER
        )

    def test_span_lifetime(self):
        """Check that the span is active for the duration of the call."""

        tracer_provider = trace_sdk.TracerProvider()
        tracer = tracer_provider.get_tracer(__name__)
        interceptor = server_interceptor(tracer)

        # To capture the current span at the time the handler is called
        active_span_in_handler = None

        def handler(request, context):
            nonlocal active_span_in_handler
            active_span_in_handler = tracer.get_current_span()
            return b""

        server = grpc.server(
            futures.ThreadPoolExecutor(), options=(("grpc.so_reuseport", 0),)
        )
        server = intercept_server(server, interceptor)
        server.add_generic_rpc_handlers((UnaryUnaryRpcHandler(handler),))

        port = server.add_insecure_port("[::]:0")
        channel = grpc.insecure_channel("localhost:{:d}".format(port))

        active_span_before_call = tracer.get_current_span()
        try:
            server.start()
            channel.unary_unary("")(b"")
        finally:
            server.stop(None)
        active_span_after_call = tracer.get_current_span()

        self.assertIsNone(active_span_before_call)
        self.assertIsNone(active_span_after_call)
        self.assertIsInstance(active_span_in_handler, trace_sdk.Span)
        self.assertIsNone(active_span_in_handler.parent)

    def test_sequential_server_spans(self):
        """Check that sequential RPCs get separate server spans."""

        tracer_provider = trace_sdk.TracerProvider()
        tracer = tracer_provider.get_tracer(__name__)

        interceptor = server_interceptor(tracer)

        # Capture the currently active span in each thread
        active_spans_in_handler = []

        def handler(request, context):
            active_spans_in_handler.append(tracer.get_current_span())
            return b""

        server = grpc.server(
            futures.ThreadPoolExecutor(), options=(("grpc.so_reuseport", 0),)
        )
        server = intercept_server(server, interceptor)
        server.add_generic_rpc_handlers((UnaryUnaryRpcHandler(handler),))

        port = server.add_insecure_port("[::]:0")
        channel = grpc.insecure_channel("localhost:{:d}".format(port))

        try:
            server.start()
            channel.unary_unary("")(b"")
            channel.unary_unary("")(b"")
        finally:
            server.stop(None)

        self.assertEqual(len(active_spans_in_handler), 2)
        span1, span2 = active_spans_in_handler
        # Spans should belong to separate traces, and each should be a root
        # span
        self.assertNotEqual(span1.context.span_id, span2.context.span_id)
        self.assertNotEqual(span1.context.trace_id, span2.context.trace_id)
        self.assertIsNone(span1.parent)
        self.assertIsNone(span1.parent)

    def test_concurrent_server_spans(self):
        """Check that concurrent RPC calls don't interfere with each other.

        This is the same check as test_sequential_server_spans except that the
        RPCs are concurrent. Two handlers are invoked at the same time on two
        separate threads. Each one should see a different active span and
        context.
        """

        tracer_provider = trace_sdk.TracerProvider()
        tracer = tracer_provider.get_tracer(__name__)

        interceptor = server_interceptor(tracer)

        # Capture the currently active span in each thread
        active_spans_in_handler = []
        latch = get_latch(2)

        def handler(request, context):
            latch()
            active_spans_in_handler.append(tracer.get_current_span())
            return b""

        server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=2),
            options=(("grpc.so_reuseport", 0),),
        )
        server = intercept_server(server, interceptor)
        server.add_generic_rpc_handlers((UnaryUnaryRpcHandler(handler),))

        port = server.add_insecure_port("[::]:0")
        channel = grpc.insecure_channel("localhost:{:d}".format(port))

        try:
            server.start()
            # Interleave calls so spans are active on each thread at the same
            # time
            with futures.ThreadPoolExecutor(max_workers=2) as tpe:
                f1 = tpe.submit(channel.unary_unary(""), b"")
                f2 = tpe.submit(channel.unary_unary(""), b"")
            futures.wait((f1, f2))
        finally:
            server.stop(None)

        self.assertEqual(len(active_spans_in_handler), 2)
        span1, span2 = active_spans_in_handler
        # Spans should belong to separate traces, and each should be a root
        # span
        self.assertNotEqual(span1.context.span_id, span2.context.span_id)
        self.assertNotEqual(span1.context.trace_id, span2.context.trace_id)
        self.assertIsNone(span1.parent)
        self.assertIsNone(span1.parent)


def get_latch(n):
    """Get a countdown latch function for use in n threads."""
    cv = threading.Condition()
    count = 0

    def countdown_latch():
        """Block until n-1 other threads have called."""
        nonlocal count
        cv.acquire()
        count += 1
        cv.notify()
        cv.release()
        cv.acquire()
        while count < n:
            cv.wait()
        cv.release()

    return countdown_latch
