import collections
import threading
import typing

from opentelemetry.sdk.trace import ReadableSpan


class SpanAccumulator:
    """
    Accumulates and batches spans in a thread-safe manner.
    """

    def __init__(self, max_len: int):
        self._max_len = max_len
        self._spans: typing.List[ReadableSpan] = []
        self._batches = collections.deque()  # fixme set max size?
        self._lock = threading.Lock()

    def nonempty(self):
        return len(self._spans) > 0 or len(self._batches) > 0

    def push(self, span: ReadableSpan) -> bool:
        with self._lock:
            self._spans.append(span)
            if len(self._spans) < self._max_len:
                return False
            self._batches.appendleft(self._spans)
            self._spans = []
            return True

    def batch(self) -> typing.List[ReadableSpan]:
        try:
            return self._batches.pop()
        except IndexError:
            # if there are no batches, batch the current spans
            with self._lock:
                out = self._spans
                self._spans = []
                return out
