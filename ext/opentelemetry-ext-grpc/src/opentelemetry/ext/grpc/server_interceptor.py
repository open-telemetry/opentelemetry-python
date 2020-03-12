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

import grpc

from opentelemetry import trace


class OpenTelemetryServerInterceptor(grpc.ServerInterceptor):
    """gRPC service interceptor that wraps each incoming request in a span.

    Usage::

        from opentelemetry.ext.grpc.server_interceptor import (
            OpenTelemetryServerInterceptor
        )

        ot_interceptor = OpenTelemetryServerInterceptor(tracer)
        server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=10),
            interceptors=(interceptor,)
        )
        ...
        server.start()


    Args:
        tracer: The tracer to use to create spans.
    """

    def __init__(self, tracer: trace.Tracer):
        self._tracer = tracer

    def intercept_service(self, continuation, handler_call_details):
        def trace_wrapper(behavior, request_streaming, response_streaming):
            """A grpc.RpcMethodHandler that wraps behavoir."""

            def new_behavior(request_or_iterator, servicer_context):
                """Wrap behavoir in a span."""
                with self._tracer.start_as_current_span(
                    _get_span_name(servicer_context),
                    kind=trace.SpanKind.SERVER,
                ):

                    response_or_iterator = behavior(
                        request_or_iterator, servicer_context
                    )

                    return response_or_iterator

            return new_behavior

        handler = continuation(handler_call_details)

        if handler.request_streaming and handler.response_streaming:
            behavior_fn = handler.stream_stream
            handler_factory = grpc.stream_stream_rpc_method_handler
        elif handler.request_streaming and not handler.response_streaming:
            behavior_fn = handler.stream_unary
            handler_factory = grpc.stream_unary_rpc_method_handler
        elif not handler.request_streaming and handler.response_streaming:
            behavior_fn = handler.unary_stream
            handler_factory = grpc.unary_stream_rpc_method_handler
        else:
            behavior_fn = handler.unary_unary
            handler_factory = grpc.unary_unary_rpc_method_handler

        new_handler = handler_factory(
            trace_wrapper(
                behavior_fn,
                handler.request_streaming,
                handler.response_streaming,
            ),
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
        return new_handler


def _get_span_name(servicer_context):
    """Get the gRPC servicer method name to use as the span name."""
    method_name = servicer_context._rpc_event.call_details.method[1:]
    if isinstance(method_name, bytes):
        method_name = method_name.decode("utf-8")
    return method_name
