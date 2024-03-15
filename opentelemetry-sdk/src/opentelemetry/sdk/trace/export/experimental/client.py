import abc
import time
import typing

import grpc

from opentelemetry.exporter.otlp.proto.common._internal import trace_encoder
from opentelemetry.proto.collector.trace.v1 import trace_service_pb2_grpc as pb
from opentelemetry.sdk.trace import ReadableSpan


class GrpcClientABC(abc.ABC):

    @abc.abstractmethod
    def send(self, batch: typing.Sequence[ReadableSpan]) -> grpc.StatusCode:
        pass


class GrpcClient(GrpcClientABC):
    """
    Exports a batch of spans to the specified endpoint. Wrap this in a RetryingGrpcClient for retry/backoff.
    """

    def __init__(
        self,
        target: str = 'localhost:4317',
        timeout_sec: int = 10,
    ):
        self._timeout_sec = timeout_sec
        self._stub = pb.TraceServiceStub(grpc.insecure_channel(target))

    def send(self, batch: typing.Sequence[ReadableSpan]) -> grpc.StatusCode:
        try:
            self._stub.Export(request=trace_encoder.encode_spans(batch), timeout=self._timeout_sec)
        except grpc.RpcError as err:
            # noinspection PyUnresolvedReferences
            return err.code()
        return grpc.StatusCode.OK


class RetryingGrpcClient(GrpcClientABC):
    """
    A GRPC client implementation that wraps another GRPC client and retries failed requests using exponential backoff.
    The `sleepfunc` arg can be passed in to fake time-based sleeping for testing.
    """

    def __init__(
        self,
        client: GrpcClientABC,
        sleepfunc: typing.Callable[[int], None] = time.sleep,
        max_retries: int = 4,
        initial_sleep_time_sec: int = 0.5,
    ):
        self._client = client
        self._sleep = sleepfunc
        self._max_retries = max_retries
        self._initial_sleep_time_sec = initial_sleep_time_sec

    def send(self, batch: typing.Sequence[ReadableSpan]) -> grpc.StatusCode:
        sleep_time_sec = self._initial_sleep_time_sec
        out = grpc.StatusCode.OK
        for i in range(self._max_retries):
            out = self._client.send(batch)
            if out == grpc.StatusCode.OK:
                return grpc.StatusCode.OK
            self._sleep(sleep_time_sec)
            sleep_time_sec *= 2
        return out


class FakeGrpcClient(GrpcClientABC):
    """
    A fake GRPC client that can be used for testing. To fake status codes, optionally set the `status_codes` arg to a
    list/tuple of status codes you want the send() method to return. If there are more calls to send() than there are
    status codes, the last status code is reused. Set the `sleep_time_sec` arg to a positive value to sleep every time
    there is a send(), simulating network transmission time.
    """

    def __init__(
        self,
        status_codes: typing.List[grpc.StatusCode] = (grpc.StatusCode.OK,),
        sleep_time_sec: int = 0,
    ):
        self._status_codes = status_codes
        self._sleep_time_sec = sleep_time_sec
        self._batches = []

    def send(self, batch: typing.Sequence[ReadableSpan]) -> grpc.StatusCode:
        time.sleep(self._sleep_time_sec)
        self._batches.append(batch)
        num_sends = len(self._batches)
        idx = min(num_sends, len(self._status_codes)) - 1
        return self._status_codes[idx]

    def get_batches(self):
        return self._batches

    def num_batches(self):
        return len(self._batches)

    def num_spans_in_batch(self, idx: int):
        return len(self._batches[idx])
