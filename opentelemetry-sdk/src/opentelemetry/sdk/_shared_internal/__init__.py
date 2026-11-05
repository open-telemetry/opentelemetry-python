# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""The batching machinery shared by the span and the log record processors.

``BatchSpanProcessor`` and ``BatchLogRecordProcessor`` both hold a
``BatchProcessor``, which owns the bounded queue, the background worker thread
and the export loop. Keeping one implementation here is what makes the two
signals behave alike on queue overflow, on shutdown and after a fork.

Everything in this module is private to the SDK and may change without a
deprecation period.
"""

from __future__ import annotations

import collections
import enum
import inspect
import logging
import os
import threading
import time
import weakref
from abc import abstractmethod
from typing import (
    Generic,
    Protocol,
    TypeVar,
)

from opentelemetry.context import (
    _SUPPRESS_INSTRUMENTATION_KEY,
    attach,
    detach,
    set_value,
)
from opentelemetry.sdk._shared_internal._processor_metrics import (
    ProcessorMetricsT,
)
from opentelemetry.util._once import Once


class DuplicateFilter(logging.Filter):
    """Filter that can be applied to internal `logger`'s.

    Currently applied to `logger`s on the export logs path to prevent endlessly logging the same log
    in cases where logging itself is failing."""

    def filter(self, record):
        """Drop a record that repeats the previous one within the same window.

        A record is treated as a repeat when its module, its level and its
        unformatted message all match the last record that passed, and both
        fall in the same 20 second window. The windows are fixed to the Unix
        epoch grid rather than measured from the last record that passed, so
        a repeat passes again as soon as the grid moves on. An export failing
        every 10 seconds, the default timeout of the OTLP log exporter, keeps
        logging at one line per window for as long as it keeps failing, which
        bounds the rate instead of stopping it.

        The state is a single previous record, so two failures alternating
        with each other both pass every time.

        Args:
            record: The ``logging.LogRecord`` about to be emitted.

        Returns:
            ``True`` to let the ``logging`` module go on handling the record,
            ``False`` to discard it.
        """
        current_log = (
            record.module,
            record.levelno,
            record.msg,
            # We need to pick a time longer than the OTLP LogExporter timeout
            # which defaults to 10 seconds, but not pick something so long that
            # it filters out useful logs.
            time.time() // 20,
        )
        if current_log != getattr(self, "last_log", None):
            self.last_log = current_log  # pylint: disable=attribute-defined-outside-init
            return True
        # False means python's `logging` module will no longer process this log.
        return False


class BatchExportStrategy(enum.Enum):
    """How many batches one pass of the export loop should send.

    ``EXPORT_ALL`` drains the queue, and is what a force flush and a shutdown
    use. ``EXPORT_WHILE_BATCH_EXCEEDS_THRESHOLD`` sends only while the queue
    still holds a full batch, which is the case when the worker was woken
    early by a burst. ``EXPORT_AT_LEAST_ONE_BATCH`` sends one batch and stops,
    which is the case when the worker woke on its own schedule.
    """

    EXPORT_ALL = 0
    EXPORT_WHILE_BATCH_EXCEEDS_THRESHOLD = 1
    EXPORT_AT_LEAST_ONE_BATCH = 2


Telemetry = TypeVar("Telemetry")


class Exporter(Protocol[Telemetry]):
    """The part of an exporter that ``BatchProcessor`` needs.

    A span exporter and a log record exporter both satisfy this, which is
    what lets one batch processor drive either of them.
    """

    @abstractmethod
    def export(self, batch: list[Telemetry], /):
        """Send one batch of telemetry.

        Args:
            batch: The items to send, oldest first, at most
                ``max_export_batch_size`` of them. The parameter is
                positional only.

        Raises:
            NotImplementedError: Always, on this base. An implementation is
                expected to catch its own transport failures rather than let
                them out, since ``BatchProcessor`` only logs what escapes.
        """
        raise NotImplementedError

    @abstractmethod
    def shutdown(self):
        """Release whatever the exporter holds and refuse further exports.

        An implementation may accept a ``timeout_millis`` keyword argument.
        ``BatchProcessor.shutdown`` inspects the signature and passes the
        remaining budget only when that argument is there.

        Raises:
            NotImplementedError: Always, on this base.
        """
        raise NotImplementedError


_logger = logging.getLogger(__name__)
_logger.addFilter(DuplicateFilter())


class BatchProcessor(Generic[Telemetry]):
    """This class can be used with exporter's that implement the above
    Exporter interface to buffer and send telemetry in batch through
     the exporter.

    The worker thread starts during construction and runs as a daemon, so it
    does not keep the interpreter alive. It wakes either when the schedule
    delay elapses or when ``emit`` has queued enough items for a full batch.

    The queue is bounded. Once it is full, the oldest item is discarded to
    make room for the newest, and the drop is counted through the metrics
    object rather than raised.

    Args:
        exporter: The exporter to hand each batch to. Its ``export`` is called
            with instrumentation suppressed, so telemetry produced by the
            export itself is not fed back into the queue.
        schedule_delay_millis: How long the worker waits between passes, in
            milliseconds. Pass 0 to remove the timeout, so that the worker
            waits for an ``emit`` and then exports at once.
        max_export_batch_size: The largest number of items handed to
            ``export`` at once. Reaching this many queued items also wakes
            the worker early.
        export_timeout_millis: Stored and not used, because there is no way
            to pass a timeout into ``export``. See
            https://github.com/open-telemetry/opentelemetry-python/issues/4555
        max_queue_size: The capacity of the queue, in items.
        exporting: The word naming the telemetry being exported, for example
            ``"span"``. It goes into the worker thread name and into the log
            messages about dropped and failed items.
        metrics: The object the processor reports its queue size, its
            finished items and its dropped items to. Pass a
            ``NoOpProcessorMetrics`` to report nothing.
    """

    def __init__(
        self,
        exporter: Exporter[Telemetry],
        schedule_delay_millis: float,
        max_export_batch_size: int,
        export_timeout_millis: float,
        max_queue_size: int,
        exporting: str,
        metrics: ProcessorMetricsT,
    ):
        """Build the processor and start its worker thread.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders. On a platform that provides
        ``os.register_at_fork``, a hook is registered so that a forked child
        rebuilds the lock, the event and the thread rather than inheriting
        them.
        """
        self._bsp_reset_once = Once()
        self._exporter = exporter
        self._max_queue_size = max_queue_size
        self._schedule_delay_millis = schedule_delay_millis
        self._schedule_delay = schedule_delay_millis / 1e3
        self._max_export_batch_size = max_export_batch_size
        # Not used. No way currently to pass timeout to export.
        # TODO(https://github.com/open-telemetry/opentelemetry-python/issues/4555): figure out what this should do.
        self._export_timeout_millis = export_timeout_millis
        # Deque is thread safe.
        self._queue = collections.deque([], max_queue_size)
        self._worker_thread = threading.Thread(
            name=f"OtelBatch{exporting}RecordProcessor",
            target=self.worker,
            daemon=True,
        )
        self._exporting = exporting

        self._shutdown = False
        self._shutdown_timeout_exceeded = False
        self._export_lock = threading.Lock()
        self._worker_awaken = threading.Event()
        self._worker_thread.start()
        if hasattr(os, "register_at_fork"):
            weak_reinit = weakref.WeakMethod(self._at_fork_reinit)

            def _after_in_child() -> None:
                """Rebuild the worker state in a freshly forked child.

                The bound method is held weakly, so the hook does nothing once
                the processor itself has been collected. That keeps a
                discarded processor from being kept alive by the fork hook,
                which ``os.register_at_fork`` never unregisters.
                """
                if reinit := weak_reinit():
                    reinit()

            os.register_at_fork(after_in_child=_after_in_child)
        self._pid = os.getpid()

        metrics.register_queue_size(lambda: len(self._queue))
        self._metrics = metrics

    def _should_export_batch(self, batch_strategy: BatchExportStrategy, num_iterations: int) -> bool:
        """Decide whether the export loop should send one more batch.

        It is called inside the export lock, so that a decision taken by the
        worker is not invalidated by a concurrent force flush.

        Args:
            batch_strategy: The strategy chosen for this pass of the loop.
            num_iterations: How many batches this pass has already sent.

        Returns:
            ``False`` when the queue is empty or the shutdown timeout has
            already been exceeded, whatever the strategy. Otherwise ``True``
            while a full batch is still queued, and after that according to
            the strategy: always for ``EXPORT_ALL``, only on the first
            iteration for ``EXPORT_AT_LEAST_ONE_BATCH``, and never for
            ``EXPORT_WHILE_BATCH_EXCEEDS_THRESHOLD``.
        """
        if not self._queue or self._shutdown_timeout_exceeded:
            return False
        # Always continue to export while queue length exceeds max batch size.
        if len(self._queue) >= self._max_export_batch_size:
            return True
        if batch_strategy is BatchExportStrategy.EXPORT_ALL:
            return True
        if batch_strategy is BatchExportStrategy.EXPORT_AT_LEAST_ONE_BATCH:
            return num_iterations == 0
        return False

    def _at_fork_reinit(self):
        """Rebuild the lock, the event, the queue and the worker thread.

        A fork copies the memory of the parent but only the calling thread,
        so the child inherits a worker thread that does not run and a lock
        that may be held by nobody reachable. Everything queued in the parent
        is discarded here rather than exported twice, so telemetry recorded
        before the fork is lost in the child.
        """
        self._export_lock = threading.Lock()
        self._worker_awaken = threading.Event()
        self._queue.clear()
        self._worker_thread = threading.Thread(
            name=f"OtelBatch{self._exporting}RecordProcessor",
            target=self.worker,
            daemon=True,
        )
        self._worker_thread.start()
        self._pid = os.getpid()

    def worker(self):
        """Run the export loop until shutdown, then drain the queue once.

        Each pass waits for the schedule delay or for ``emit`` to signal that
        a full batch is queued, and picks the strategy from which of the two
        happened. A schedule delay of 0 removes the timeout rather than the
        wait: the worker blocks until an ``emit`` or a shutdown wakes it, and
        then drains the queue, so telemetry is exported as soon as it is
        recorded.

        The final pass after the loop exits runs with ``EXPORT_ALL``, which
        is how telemetry queued just before a shutdown still reaches the
        exporter, as long as the shutdown timeout has not elapsed.
        """
        while not self._shutdown:
            # Lots of strategies in the spec for setting next timeout.
            # https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/trace/sdk.md#batching-processor.
            # Shutdown will interrupt this sleep. Emit will interrupt this sleep only if the queue is bigger then threshold,
            # or on every emit when the schedule delay is 0, in which case there is no timeout and telemetry is exported
            # as soon as it is emitted.
            sleep_interrupted = self._worker_awaken.wait(self._schedule_delay or None)
            if self._shutdown:
                break
            # Clear before exporting so that an emit during the export wakes the worker again.
            self._worker_awaken.clear()
            if self._schedule_delay == 0:
                batch_strategy = BatchExportStrategy.EXPORT_ALL
            elif sleep_interrupted:
                batch_strategy = BatchExportStrategy.EXPORT_WHILE_BATCH_EXCEEDS_THRESHOLD
            else:
                batch_strategy = BatchExportStrategy.EXPORT_AT_LEAST_ONE_BATCH
            self._export(batch_strategy)
        self._export(BatchExportStrategy.EXPORT_ALL)

    def _export(self, batch_strategy: BatchExportStrategy) -> None:
        """Send batches to the exporter until the strategy says to stop.

        The whole loop runs under the export lock, so a force flush and the
        worker never hand overlapping batches to the exporter. Instrumentation
        is suppressed around each ``export`` call, which stops the export path
        from recording telemetry about itself.

        An exception raised by the exporter is caught and logged, and the loop
        goes on with the next batch. The items in the failed batch have
        already been removed from the queue and already counted as finished,
        so they are not retried.

        Args:
            batch_strategy: How many batches this call should send, as
                interpreted by ``_should_export_batch``.
        """
        with self._export_lock:
            iteration = 0
            # We could see concurrent export calls from worker and force_flush. We call _should_export_batch
            # once the lock is obtained to see if we still need to make the requested export.
            while self._should_export_batch(batch_strategy, iteration):
                iteration += 1
                token = attach(set_value(_SUPPRESS_INSTRUMENTATION_KEY, True))
                count = min(
                    self._max_export_batch_size,
                    len(self._queue),
                )
                # Oldest records are at the back, so pop from there.
                batch = [self._queue.pop() for _ in range(count)]
                # Record on submission to the exporter.
                self._metrics.finish_items(count)
                try:
                    self._exporter.export(batch)
                except Exception:  # pylint: disable=broad-exception-caught
                    _logger.exception("Exception while exporting %s.", self._exporting)
                detach(token)

    def emit(self, data: Telemetry) -> None:
        """Queue one item for export.

        The call does not block on the exporter. After a shutdown the item is
        discarded and counted with the ``already_shutdown`` error type. When
        the queue is already at capacity the oldest item is discarded to make
        room and counted with the ``queue_full`` error type, so a slow
        exporter costs the oldest telemetry rather than the newest.

        When the process id has changed since construction, the worker state
        is rebuilt first, which discards whatever the parent had queued.

        Args:
            data: The span or log record to queue. It is stored as it is,
                without copying, so a later mutation of a still-queued item
                is visible to the exporter.
        """
        if self._shutdown:
            _logger.info("Shutdown called, ignoring %s.", self._exporting)
            self._metrics.drop_items(1, "already_shutdown")
            return
        if self._pid != os.getpid():
            self._bsp_reset_once.do_once(self._at_fork_reinit)
        if len(self._queue) == self._max_queue_size:
            _logger.warning("Queue full, dropping %s.", self._exporting)
            self._metrics.drop_items(1)
        # This will drop a log from the right side if the queue is at _max_queue_size.
        self._queue.appendleft(data)
        if (
            self._schedule_delay == 0 or len(self._queue) >= self._max_export_batch_size
        ) and not self._worker_awaken.is_set():
            self._worker_awaken.set()

    def shutdown(self, timeout_millis: int = 30000):
        """Stop accepting telemetry, drain what is queued, close the exporter.

        A second call returns at once and does nothing. After the first call
        ``emit`` drops everything it is given and ``force_flush`` returns
        ``False``.

        The worker is woken, then joined for up to the whole timeout. Whatever
        is left of the budget after the join is passed to the exporter, but
        only when its ``shutdown`` declares a ``timeout_millis`` argument.
        The method can return while one export is still in flight, since it
        does not wait for the worker a second time.

        Args:
            timeout_millis: The budget for the join and the exporter shutdown
                together, in milliseconds. Telemetry still queued when it runs
                out is discarded without being exported.
        """
        if self._shutdown:
            return
        shutdown_should_end = time.time() + (timeout_millis / 1000)
        # Causes emit to reject telemetry and makes force_flush a no-op.
        self._shutdown = True
        # Interrupts sleep in the worker if it's sleeping.
        self._worker_awaken.set()
        self._worker_thread.join(timeout_millis / 1000)
        # Stops worker thread from calling export again if queue is still not empty.
        self._shutdown_timeout_exceeded = True
        # We want to shutdown immediately only if we already waited `timeout_secs`.
        # Otherwise we pass the remaining timeout to the exporter.
        # Some exporter's shutdown support a timeout param.
        if "timeout_millis" in inspect.getfullargspec(self._exporter.shutdown).args:
            remaining_millis = (shutdown_should_end - time.time()) * 1000
            self._exporter.shutdown(timeout_millis=max(0, remaining_millis))  # type: ignore
        else:
            self._exporter.shutdown()
        # Worker thread **should** be finished at this point, because we called shutdown on the exporter,
        # and set shutdown_is_occuring to prevent further export calls. It's possible that a single export
        # call is ongoing and the thread isn't finished. In this case we will return instead of waiting on
        # the thread to finish.

    # TODO: Fix force flush so the timeout is used https://github.com/open-telemetry/opentelemetry-python/issues/4568.
    def force_flush(self, timeout_millis: int | None = None) -> bool:
        """Export everything queued, blocking until the queue is empty.

        The call takes the export lock, so it waits for a batch the worker is
        already sending before starting its own.

        Args:
            timeout_millis: Ignored. The call blocks until the queue is
                drained however long that takes. See
                https://github.com/open-telemetry/opentelemetry-python/issues/4568

        Returns:
            ``True`` once the queue has been drained. ``False`` when the
            processor has been shut down, in which case nothing was
            exported.
        """
        if self._shutdown:
            return False
        # Blocking call to export.
        self._export(BatchExportStrategy.EXPORT_ALL)
        return True
