import threading
import typing

from opentelemetry.sdk.trace import ReadableSpan


class SpanAccumulator:
    """
    Accumulates and batches spans in a thread-safe manner.
    """

    def __init__(self):
        self._q = []
        self._lock = threading.Lock()

    def push(self, span: ReadableSpan) -> int:
        with self._lock:
            self._q.append(span)
            return len(self._q)

    def batch(self) -> typing.List[ReadableSpan]:
        with self._lock:
            out = self._q
            self._q = []
            return out
