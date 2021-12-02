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

import abc
import collections
import enum
import logging
import os
import sys
import threading
from os import linesep
from typing import IO, Callable, Deque, List, Optional, Sequence

from opentelemetry.context import attach, detach, set_value
from opentelemetry.sdk._logs import LogData, LogProcessor, LogRecord
from opentelemetry.util._time import _time_ns

_logger = logging.getLogger(__name__)


class LogExportResult(enum.Enum):
    SUCCESS = 0
    FAILURE = 1


class LogExporter(abc.ABC):
    """Interface for exporting logs.

    Interface to be implemented by services that want to export logs received
    in their own format.

    To export data this MUST be registered to the :class`opentelemetry.sdk._logs.LogEmitter` using a
    log processor.
    """

    @abc.abstractmethod
    def export(self, batch: Sequence[LogData]):
        """Exports a batch of logs.

        Args:
            batch: The list of `LogData` objects to be exported

        Returns:
            The result of the export
        """

    @abc.abstractmethod
    def shutdown(self):
        """Shuts down the exporter.

        Called when the SDK is shut down.
        """


class ConsoleLogExporter(LogExporter):
    """Implementation of :class:`LogExporter` that prints log records to the
    console.

    This class can be used for diagnostic purposes. It prints the exported
    log records to the console STDOUT.
    """

    def __init__(
        self,
        out: IO = sys.stdout,
        formatter: Callable[[LogRecord], str] = lambda record: record.to_json()
        + linesep,
    ):
        self.out = out
        self.formatter = formatter

    def export(self, batch: Sequence[LogData]):
        for data in batch:
            self.out.write(self.formatter(data.log_record))
        self.out.flush()
        return LogExportResult.SUCCESS

    def shutdown(self):
        pass


class SimpleLogProcessor(LogProcessor):
    """This is an implementation of LogProcessor which passes
    received logs in the export-friendly LogData representation to the
    configured LogExporter, as soon as they are emitted.
    """

    def __init__(self, exporter: LogExporter):
        self._exporter = exporter
        self._shutdown = False

    def emit(self, log_data: LogData):
        if self._shutdown:
            _logger.warning("Processor is already shutdown, ignoring call")
            return
        token = attach(set_value("suppress_instrumentation", True))
        try:
            self._exporter.export((log_data,))
        except Exception:  # pylint: disable=broad-except
            _logger.exception("Exception while exporting logs.")
        detach(token)

    def shutdown(self):
        self._shutdown = True
        self._exporter.shutdown()

    def force_flush(
        self, timeout_millis: int = 30000
    ) -> bool:  # pylint: disable=no-self-use
        return True


class _FlushRequest:
    __slots__ = ["event", "num_log_records"]

    def __init__(self):
        self.event = threading.Event()
        self.num_log_records = 0


class BatchLogProcessor(LogProcessor):
    """This is an implementation of LogProcessor which creates batches of
    received logs in the export-friendly LogData representation and
    send to the configured LogExporter, as soon as they are emitted.
    """

    def __init__(
        self,
        exporter: LogExporter,
        schedule_delay_millis: int = 5000,
        max_export_batch_size: int = 512,
        export_timeout_millis: int = 30000,
    ):
        self._exporter = exporter
        self._schedule_delay_millis = schedule_delay_millis
        self._max_export_batch_size = max_export_batch_size
        self._export_timeout_millis = export_timeout_millis
        self._queue = collections.deque()  # type: Deque[LogData]
        self._worker_thread = threading.Thread(target=self.worker, daemon=True)
        self._condition = threading.Condition(threading.Lock())
        self._shutdown = False
        self._flush_request = None  # type: Optional[_FlushRequest]
        self._log_records = [
            None
        ] * self._max_export_batch_size  # type: List[Optional[LogData]]
        self._worker_thread.start()
        # Only available in *nix since py37.
        if hasattr(os, "register_at_fork"):
            os.register_at_fork(
                after_in_child=self._at_fork_reinit
            )  # pylint: disable=protected-access

    def _at_fork_reinit(self):
        self._condition = threading.Condition(threading.Lock())
        self._queue.clear()
        self._worker_thread = threading.Thread(target=self.worker, daemon=True)
        self._worker_thread.start()

    def worker(self):
        timeout = self._schedule_delay_millis / 1e3
        flush_request = None  # type: Optional[_FlushRequest]
        while not self._shutdown:
            with self._condition:
                if self._shutdown:
                    # shutdown may have been called, avoid further processing
                    break
                flush_request = self._get_and_unset_flush_request()
                if (
                    len(self._queue) < self._max_export_batch_size
                    and self._flush_request is None
                ):
                    self._condition.wait(timeout)

                    flush_request = self._get_and_unset_flush_request()
                    if not self._queue:
                        timeout = self._schedule_delay_millis / 1e3
                        self._notify_flush_request_finished(flush_request)
                        flush_request = None
                        continue
                    if self._shutdown:
                        break

            start_ns = _time_ns()
            self._export(flush_request)
            end_ns = _time_ns()
            # subtract the duration of this export call to the next timeout
            timeout = self._schedule_delay_millis / 1e3 - (
                (end_ns - start_ns) / 1e9
            )

            self._notify_flush_request_finished(flush_request)
            flush_request = None

        # there might have been a new flush request while export was running
        # and before the done flag switched to true
        with self._condition:
            shutdown_flush_request = self._get_and_unset_flush_request()

        # flush the remaining logs
        self._drain_queue()
        self._notify_flush_request_finished(flush_request)
        self._notify_flush_request_finished(shutdown_flush_request)

    def _export(self, flush_request: Optional[_FlushRequest] = None):
        """Exports logs considering the given flush_request.

        If flush_request is not None then logs are exported in batches
        until the number of exported logs reached or exceeded the num of logs in
        flush_request, otherwise exports at max max_export_batch_size logs.
        """
        if flush_request is None:
            self._export_batch()
            return

        num_log_records = flush_request.num_log_records
        while self._queue:
            exported = self._export_batch()
            num_log_records -= exported

            if num_log_records <= 0:
                break

    def _export_batch(self) -> int:
        """Exports at most max_export_batch_size logs and returns the number of
        exported logs.
        """
        idx = 0
        while idx < self._max_export_batch_size and self._queue:
            record = self._queue.pop()
            self._log_records[idx] = record
            idx += 1
        token = attach(set_value("suppress_instrumentation", True))
        try:
            self._exporter.export(self._log_records[:idx])  # type: ignore
        except Exception:  # pylint: disable=broad-except
            _logger.exception("Exception while exporting logs.")
        detach(token)

        for index in range(idx):
            self._log_records[index] = None
        return idx

    def _drain_queue(self):
        """Export all elements until queue is empty.

        Can only be called from the worker thread context because it invokes
        `export` that is not thread safe.
        """
        while self._queue:
            self._export_batch()

    def _get_and_unset_flush_request(self) -> Optional[_FlushRequest]:
        flush_request = self._flush_request
        self._flush_request = None
        if flush_request is not None:
            flush_request.num_log_records = len(self._queue)
        return flush_request

    @staticmethod
    def _notify_flush_request_finished(
        flush_request: Optional[_FlushRequest] = None,
    ):
        if flush_request is not None:
            flush_request.event.set()

    def _get_or_create_flush_request(self) -> _FlushRequest:
        if self._flush_request is None:
            self._flush_request = _FlushRequest()
        return self._flush_request

    def emit(self, log_data: LogData) -> None:
        """Adds the `LogData` to queue and notifies the waiting threads
        when size of queue reaches max_export_batch_size.
        """
        if self._shutdown:
            return
        self._queue.appendleft(log_data)
        if len(self._queue) >= self._max_export_batch_size:
            with self._condition:
                self._condition.notify()

    def shutdown(self):
        self._shutdown = True
        with self._condition:
            self._condition.notify_all()
        self._worker_thread.join()
        self._exporter.shutdown()

    def force_flush(self, timeout_millis: Optional[int] = None) -> bool:
        if timeout_millis is None:
            timeout_millis = self._export_timeout_millis
        if self._shutdown:
            return True

        with self._condition:
            flush_request = self._get_or_create_flush_request()
            self._condition.notify_all()

        ret = flush_request.event.wait(timeout_millis / 1e3)
        if not ret:
            _logger.warning("Timeout was exceeded in force_flush().")
        return ret
