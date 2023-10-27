# Copyright The OpenTelemetry Authors
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

import asyncio
import logging
from typing import List, Optional
from logging import getLogger

from opentelemetry import context as context_api
from opentelemetry.sdk.trace import ReadableSpan, Span
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SpanExporter,
    SpanProcessor,
)
from opentelemetry.sdk.trace.export._async.loop import (
    run_in_otel_event_loop,
)

_logger = getLogger(__name__)


class _BlockableEvent(asyncio.Event):
    """Equivalent to `asyncio.Event` but provides `set_and_wait` which blocks until the event
    is cleared"""

    def __init__(self) -> None:
        super().__init__()
        self._clear_event = asyncio.Event()

    def clear(self) -> None:
        super().clear()
        self._clear_event.set()

    async def set_and_wait(self) -> None:
        """Similar to set() but blocks until the event to cleared (probably by the waiter)"""
        self.set()
        await self._clear_event.wait()
        self._clear_event.clear()


async def _wait_event(e: asyncio.Event, timeout: float) -> bool:
    """Similar to `Event.wait` but returns a bool instead of throwing

    True indicates the event was set, False that is was not set within timeout
    """
    try:
        await asyncio.wait_for(e.wait(), timeout)
        return True
    except TimeoutError:
        return False


class _Worker:
    def __init__(
        self,
        *,
        span_exporter: SpanExporter,
        max_queue_size: int,
        schedule_delay_millis: float,
        max_export_batch_size: int,
        export_timeout_millis: float,
    ) -> None:
        self._span_exporter = span_exporter
        self._schedule_delay_millis = schedule_delay_millis
        self._max_export_batch_size = max_export_batch_size
        self._max_queue_size = max_queue_size
        self._export_timeout_millis = export_timeout_millis
        self._span_exporter = span_exporter

        self._lqueue: List[ReadableSpan] = []
        self._flush_event = _BlockableEvent()
        self._worker_task: asyncio.Task[None]

    async def _start(self) -> None:
        self._worker_task = asyncio.create_task(self._worker())

    async def _worker(self) -> None:
        while True:
            should_flush = await _wait_event(
                self._flush_event, self._schedule_delay_millis / 1000
            )
            if should_flush:
                await self._drain_queue()
                self._flush_event.clear()
                continue

            await self._export_batch()

    async def _export_batch(self) -> None:
        spans = self._lqueue[: self._max_export_batch_size]
        self._lqueue = self._lqueue[self._max_export_batch_size :]

        _logger.info("Doing export of %s spans!", len(spans))
        # unfortunately any use of ThreadPoolExecutors doesn't work in atexit hooks. See
        # https://github.com/python/cpython/issues/86813. If it fails with RuntimeError,
        # try again blocking the event loop
        try:
            await asyncio.to_thread(self._span_exporter.export, spans)
        except RuntimeError:
            logging.warn(
                "ThreadPoolExecutor was already shutdown, exporting synchronously in event loop thread. "
                "This might be running in an atexit hook."
            )
            self._span_exporter.export(spans)

    async def _drain_queue(self) -> None:
        # do in while loop as more spans could be enqueued while awaiting export
        _logger.info("_drain_queue() export of %s spans!", len(self._lqueue))
        while self._lqueue:
            await self._export_batch()

    async def _enqueue(self, span: ReadableSpan) -> None:
        if len(self._lqueue) > self._max_queue_size:
            # drop the span
            _logger.info("Queue is full, dropping span!")
            return

        self._lqueue.append(span)

    async def _shutdown(self) -> None:
        self._worker_task.cancel()
        try:
            await self._worker_task
        except asyncio.CancelledError:
            _logger.info("worker task cancelled")
            pass
        _logger.info("Draining queue")
        await self._drain_queue()

    async def _force_flush(self) -> None:
        await self._flush_event.set_and_wait()

    # Public thread safe API
    start = run_in_otel_event_loop(_start)
    enqueue = run_in_otel_event_loop(_enqueue)
    shutdown = run_in_otel_event_loop(_shutdown)
    force_flush = run_in_otel_event_loop(_force_flush)


class AsyncBatchSpanProcessor(SpanProcessor):
    def __init__(
        self,
        span_exporter: SpanExporter,
        *,
        max_queue_size: Optional[int] = None,
        schedule_delay_millis: Optional[float] = None,
        max_export_batch_size: Optional[int] = None,
        export_timeout_millis: Optional[float] = None,
    ):
        if max_queue_size is None:
            max_queue_size = BatchSpanProcessor._default_max_queue_size()

        if schedule_delay_millis is None:
            schedule_delay_millis = (
                BatchSpanProcessor._default_schedule_delay_millis()
            )

        if max_export_batch_size is None:
            max_export_batch_size = (
                BatchSpanProcessor._default_max_export_batch_size()
            )

        if export_timeout_millis is None:
            export_timeout_millis = (
                BatchSpanProcessor._default_export_timeout_millis()
            )

        BatchSpanProcessor._validate_arguments(
            max_queue_size, schedule_delay_millis, max_export_batch_size
        )

        self._worker = _Worker(
            span_exporter=span_exporter,
            max_queue_size=max_queue_size,
            schedule_delay_millis=schedule_delay_millis,
            max_export_batch_size=max_export_batch_size,
            export_timeout_millis=export_timeout_millis,
        )
        self._worker.start().result()

    def on_start(
        self,
        span: Span,
        parent_context: Optional[context_api.Context] = None,
    ) -> None:
        pass

    def on_end(self, span: ReadableSpan) -> None:
        self._worker.enqueue(span).result()

    def shutdown(self) -> None:
        self._worker.shutdown().result()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        try:
            self._worker.force_flush().result(timeout=timeout_millis / 1000)
            return True
        except TimeoutError:
            return False
