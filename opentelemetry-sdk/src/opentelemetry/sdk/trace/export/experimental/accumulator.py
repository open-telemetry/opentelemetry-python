import collections
import threading
import typing

from opentelemetry.sdk.trace import ReadableSpan


class SpanAccumulator:
    """
    A thread-safe container designed to collect and batch spans. It accumulates spans until a specified batch size is
    reached, at which point the accumulated spans are moved into a FIFO queue. Provides methods to add spans, check if
    the accumulator is non-empty, and retrieve the earliest batch of spans from the queue.
    """

    def __init__(self, batch_size: int):
        self._batch_size = batch_size
        self._spans: typing.List[ReadableSpan] = []
        self._batches = collections.deque()  # fixme set max size
        self._lock = threading.Lock()

    def nonempty(self) -> bool:
        """
        Checks if the accumulator contains any spans or batches. It returns True if either the span list or the batch
        queue is non-empty, and False otherwise.
        """
        with self._lock:
            return len(self._spans) > 0 or len(self._batches) > 0

    def push(self, span: ReadableSpan) -> bool:
        """
        Adds a span to the accumulator. If the addition causes the number of spans to reach the
        specified batch size, the accumulated spans are moved into a FIFO queue as a new batch. Returns True if a new
        batch was created, otherwise returns False.
        """
        with self._lock:
            self._spans.append(span)
            if len(self._spans) < self._batch_size:
                return False
            self._batches.appendleft(self._spans)
            self._spans = []
            return True

    def batch(self) -> typing.List[ReadableSpan]:
        """
        Returns the earliest (first in line) batch of spans from the FIFO queue. If the queue is empty, returns any
        remaining spans that haven't been batched.
        """
        try:
            return self._batches.pop()
        except IndexError:
            # if there are no batches left, return the current spans
            with self._lock:
                out = self._spans
                self._spans = []
                return out
