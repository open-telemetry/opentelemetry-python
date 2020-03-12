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

import collections

import grpc
from grpc.framework.foundation import future
from grpc.framework.interfaces.face import face


class _ClientCallDetails(
    collections.namedtuple(
        "_ClientCallDetails", ("method", "timeout", "metadata", "credentials")
    ),
    grpc.ClientCallDetails,
):
    pass


# TODO
# https://github.com/c24t/grpc/blob/50619a562f50ef7ee680ed5ce35de94b5a3b1539/src/python/grpcio/grpc/__init__.py#L561
# https://github.com/census-instrumentation/opencensus-python/pull/617/files#diff-16ff5c7896222cfa69b7aed98860f7d3R50
class WrappedResponseIterator(future.Future, face.Call):
    """Wraps the rpc response iterator.

    The grpc.StreamStreamClientInterceptor abstract class states stream
    interceptor method should return an object that's both a call (implementing
    the response iterator) and a future.  Thus, this class is a thin wrapper
    around the rpc response to provide the opencensus extension.

    :type iterator: (future.Future, face.Call)
    :param iterator: rpc response iterator

    :type span: opencensus.trace.Span
    :param span: rpc span
    """

    def __init__(self, iterator, span):
        self._iterator = iterator
        self._span = span

        # TODO
        # self._messages_received = 0

    def add_done_callback(self, fn):
        self._iterator.add_done_callback(lambda ignored_callback: fn(self))

    def __iter__(self):
        return self

    def __next__(self):
        try:
            message = next(self._iterator)
        except StopIteration:
            print("end wrapper iterator")
            # execution_context.get_opencensus_tracer().end_span()
            raise

        # self._messages_received += 1
        # add_message_event(
        #     proto_message=message,
        #     span=self._span,
        #     message_event_type=time_event.Type.RECEIVED,
        #     message_id=self._messages_received)

        return message

    def next(self):
        return self.__next__()

    def cancel(self):
        return self._iterator.cancel()

    def is_active(self):
        return self._iterator.is_active()

    def cancelled(self):
        raise NotImplementedError()  # pragma: NO COVER

    def running(self):
        raise NotImplementedError()  # pragma: NO COVER

    def done(self):
        raise NotImplementedError()  # pragma: NO COVER

    def result(self, timeout=None):
        raise NotImplementedError()  # pragma: NO COVER

    def exception(self, timeout=None):
        raise NotImplementedError()  # pragma: NO COVER

    def traceback(self, timeout=None):
        raise NotImplementedError()  # pragma: NO COVER

    def initial_metadata(self):
        raise NotImplementedError()  # pragma: NO COVER

    def terminal_metadata(self):
        raise NotImplementedError()  # pragma: NO COVER

    def code(self):
        raise NotImplementedError()  # pragma: NO COVER

    def details(self):
        raise NotImplementedError()  # pragma: NO COVER

    def time_remaining(self):
        raise NotImplementedError()  # pragma: NO COVER

    def add_abortion_callback(self, abortion_callback):
        raise NotImplementedError()  # pragma: NO COVER

    def protocol_context(self):
        raise NotImplementedError()  # pragma: NO COVER


class OpenTelemetryClientInterceptor(
    grpc.UnaryUnaryClientInterceptor,
    grpc.UnaryStreamClientInterceptor,
    grpc.StreamUnaryClientInterceptor,
    grpc.StreamStreamClientInterceptor,
):
    def _intercept_call(
        self,
        client_call_details,
        request_iterator,
        request_streaming,
        response_streaming,
    ):
        # TODO
        return client_call_details, request_iterator, None

    def _callback(self, span):
        def callback(future_response):
            pass

            # TODO
            # grpc_utils.add_message_event(
            #     proto_message=future_response.result(),
            #     span=current_span,
            #     message_event_type=time_event.Type.RECEIVED,
            # )
            # self._trace_future_exception(future_response)
            # self.tracer.end_span()

        return callback

    def intercept_unary_unary(
        self, continuation, client_call_details, request
    ):
        new_details, new_request, current_span = self._intercept_call(
            client_call_details=client_call_details,
            request_iterator=iter((request,)),
            request_streaming=False,
            response_streaming=False,
        )

        response = continuation(new_details, next(new_request))

        response.add_done_callback(self._callback(current_span))

        return response

    def intercept_unary_stream(
        self, continuation, client_call_details, request
    ):
        new_details, new_request_iterator, current_span = self._intercept_call(
            client_call_details=client_call_details,
            request_iterator=iter((request,)),
            request_streaming=False,
            response_streaming=True,
        )

        return WrappedResponseIterator(
            continuation(new_details, next(new_request_iterator)), current_span
        )

    def intercept_stream_unary(
        self, continuation, client_call_details, request_iterator
    ):
        new_details, new_request_iterator, current_span = self._intercept_call(
            client_call_details=client_call_details,
            request_iterator=request_iterator,
            request_streaming=True,
            response_streaming=False,
        )

        response = continuation(new_details, new_request_iterator)

        response.add_done_callback(self._callback(current_span))

        return response

    def intercept_stream_stream(
        self, continuation, client_call_details, request_iterator
    ):
        new_details, new_request_iterator, current_span = self._intercept_call(
            client_call_details=client_call_details,
            request_iterator=request_iterator,
            request_streaming=True,
            response_streaming=True,
        )

        return WrappedResponseIterator(
            continuation(new_details, new_request_iterator), current_span
        )
