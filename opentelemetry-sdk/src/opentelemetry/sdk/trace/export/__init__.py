# Copyright 2019, OpenTelemetry Authors
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

import logging
import queue
import threading
import typing
from enum import Enum

from .. import Span, SpanProcessor

logger = logging.getLogger(__name__)


class SpanExportResult(Enum):
    SUCCESS = 0
    FAILED_RETRYABLE = 1
    FAILED_NOT_RETRYABLE = 2


class SpanExporter:
    """Interface for exporting spans.

    Interface to be implemented by services that want to export recorded in
    its own format.

    To export data this MUST be registered to the :class`..Tracer` using a
    `SimpleExportSpanProcessor` or a `BatchSpanProcessor`.
    """

    def export(self, spans: typing.Sequence[Span]) -> "SpanExportResult":
        """Exports a batch of telemetry data.

        Args:
            spans: The list of `Span`s to be exported

        Returns:
            The result of the export
        """

    def shutdown(self) -> None:
        """Shuts down the exporter.

        Called when the SDK is shut down.
        """


class SimpleExportSpanProcessor(SpanProcessor):
    """Simple SpanProcessor implementation.

    SimpleExportSpanProcessor is an implementation of `SpanProcessor` that
    passes ended spans directly to the configured `SpanExporter`.
    """

    def __init__(self, span_exporter: SpanExporter):
        self.span_exporter = span_exporter

    def on_start(self, span: Span) -> None:
        pass

    def on_end(self, span: Span) -> None:
        try:
            self.span_exporter.export((span,))
        # pylint: disable=broad-except
        except Exception as exc:
            logger.warning("Exception while exporting data: %s", exc)

    def shutdown(self) -> None:
        self.span_exporter.shutdown()


class BatchExportSpanProcessor(SpanProcessor):
    """Batch span processor implementation.

    BatchExportSpanProcessor is an implementation of `SpanProcessor` that
    batches ended spans and pushes them to the configured `SpanExporter`.
    """

    def __init__(
        self,
        span_exporter: SpanExporter,
        max_queue_size: int = 2048,
        schedule_delay_millis: float = 5000,
        max_export_batch_size: int = 512,
    ):
        if max_queue_size <= 0:
            raise ValueError("max_queue_size must be a positive integer.")

        if schedule_delay_millis <= 0:
            raise ValueError("schedule_delay_millis must be positive.")

        if max_export_batch_size <= 0:
            raise ValueError(
                "max_export_batch_size must be a positive integer."
            )

        if max_export_batch_size > max_queue_size:
            raise ValueError(
                "max_export_batch_size must be less and equal to max_export_batch_size."
            )

        self.span_exporter = span_exporter
        self.queue = queue.Queue(max_queue_size)
        self.worker_thread = threading.Thread(target=self.worker, daemon=True)
        self.condition = threading.Condition()
        self.schedule_delay_millis = schedule_delay_millis
        self.max_export_batch_size = max_export_batch_size
        self.half_max_queue_size = max_queue_size // 2
        self.done = False

        self.worker_thread.start()

    def on_start(self, span: Span) -> None:
        pass

    def on_end(self, span: Span) -> None:
        try:
            self.queue.put(span, block=False)
        except queue.Full:
            # TODO: dropped spans counter?
            pass
        if self.queue.qsize() >= self.half_max_queue_size:
            with self.condition:
                self.condition.notify_all()

    def worker(self):
        while not self.done:
            if self.queue.qsize() < self.max_export_batch_size:
                with self.condition:
                    self.condition.wait(self.schedule_delay_millis / 1000)
                    if self.queue.empty():
                        # spurious notification, let's wait again
                        continue
                    if self.done:
                        # missing spans will be sent when calling flush
                        break

            self.export()

        # be sure that all spans are sent
        self._flush()

    def export(self):
        """Exports at most max_export_batch_size spans."""
        idx = 0
        spans = []
        # currently only a single thread acts as consumer, so queue.get() will
        # never block
        while idx < self.max_export_batch_size and not self.queue.empty():
            spans.append(self.queue.get())
            idx += 1
        try:
            self.span_exporter.export(spans)
        # pylint: disable=broad-except
        except Exception as exc:
            logger.warning("Exception while exporting data: %s", exc)

    def _flush(self):
        while not self.queue.empty():
            self.export()

    def shutdown(self) -> None:
        # signal the worker thread to finish and then wait for it
        self.done = True
        with self.condition:
            self.condition.notify_all()
        self.worker_thread.join()
        self.span_exporter.shutdown()
