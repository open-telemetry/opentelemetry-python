import typing

from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor, Span
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.sdk.trace.export.experimental.accumulator import SpanAccumulator
from opentelemetry.sdk.trace.export.experimental.timer import TimerABC, PeriodicTimer


class BatchSpanProcessor2(SpanProcessor):
    """
    A SpanProcessor that sends spans in batches on an interval or when a maximum number of spans has been reached,
    whichever comes first.
    """

    def __init__(
        self,
        exporter: SpanExporter,
        max_batch_size: int = 1024,
        interval_sec: int = 4,
        timer: typing.Optional[TimerABC] = None,
    ):
        self._exporter = exporter
        self._accumulator = SpanAccumulator(max_batch_size)
        self._timer = timer or PeriodicTimer(interval_sec)
        self._timer.set_callback(self._export_batch)
        self._timer.start()

    def on_start(self, span: Span, parent_context: typing.Optional[Context] = None) -> None:
        pass

    def on_end(self, span: ReadableSpan) -> None:
        """
        This method must be extremely fast. It adds the span to the accumulator for later sending and pokes the timer
        if the number of spans waiting to be sent has reached the maximum batch size.
        """
        full = self._accumulator.push(span)
        if full:
            self._timer.poke()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """
        Stops the timer, exports any spans in the accumulator then restarts the timer.
        """
        self._timer.stop()
        self._exporter.force_flush(timeout_millis)  # this may be a no-op depending on the impl
        while self._accumulator.nonempty():
            result = self._export_batch()
            if result != SpanExportResult.SUCCESS:
                return False
        self._timer.start()

    def shutdown(self) -> None:
        self._timer.stop()
        while self._accumulator.nonempty():
            self._export_batch()
        self._exporter.shutdown()

    def _export_batch(self) -> SpanExportResult:
        """
        This is the timer's callback. It runs on its own thread.
        """
        batch = self._accumulator.batch()
        if len(batch) > 0:
            return self._exporter.export(batch)
        return SpanExportResult.SUCCESS
