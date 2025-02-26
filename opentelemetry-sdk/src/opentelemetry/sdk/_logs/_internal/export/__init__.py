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
import weakref
from os import environ, linesep
from time import time_ns
from typing import IO, Callable, Deque, List, Optional, Sequence

from opentelemetry.context import (
    _SUPPRESS_INSTRUMENTATION_KEY,
    attach,
    detach,
    set_value,
)
from opentelemetry.sdk._logs import LogData, LogRecord, LogRecordProcessor
from opentelemetry.sdk.environment_variables import (
    OTEL_BLRP_EXPORT_TIMEOUT,
    OTEL_BLRP_MAX_EXPORT_BATCH_SIZE,
    OTEL_BLRP_MAX_QUEUE_SIZE,
    OTEL_BLRP_SCHEDULE_DELAY,
)
from opentelemetry.util._once import Once

_DEFAULT_SCHEDULE_DELAY_MILLIS = 5000
_DEFAULT_MAX_EXPORT_BATCH_SIZE = 512
_DEFAULT_EXPORT_TIMEOUT_MILLIS = 30000
_DEFAULT_MAX_QUEUE_SIZE = 2048
_ENV_VAR_INT_VALUE_ERROR_MESSAGE = (
    "Unable to parse value for %s as integer. Defaulting to %s."
)

_logger = logging.getLogger(__name__)


class LogExportResult(enum.Enum):
    SUCCESS = 0
    FAILURE = 1


class LogExporter(abc.ABC):
    """Interface for exporting logs.

    Interface to be implemented by services that want to export logs received
    in their own format.

    To export data this MUST be registered to the :class`opentelemetry.sdk._logs.Logger` using a
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


class SimpleLogRecordProcessor(LogRecordProcessor):
    """This is an implementation of LogRecordProcessor which passes
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
        token = attach(set_value(_SUPPRESS_INSTRUMENTATION_KEY, True))
        try:
            self._exporter.export((log_data,))
        except Exception:  # pylint: disable=broad-exception-caught
            _logger.exception("Exception while exporting logs.")
        detach(token)

    def shutdown(self):
        self._shutdown = True
        self._exporter.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:  # pylint: disable=no-self-use
        return True


class _FlushRequest:
    __slots__ = ["event", "num_log_records"]

    def __init__(self):
        self.event = threading.Event()
        self.num_log_records = 0


_BSP_RESET_ONCE = Once()


class BatchLogRecordProcessor(LogRecordProcessor):
    """This is an implementation of LogRecordProcessor which creates batches of
    received logs in the export-friendly LogData representation and
    send to the configured LogExporter, as soon as they are emitted.

    `BatchLogRecordProcessor` is configurable with the following environment
    variables which correspond to constructor parameters:

    - :envvar:`OTEL_BLRP_SCHEDULE_DELAY`
    - :envvar:`OTEL_BLRP_MAX_QUEUE_SIZE`
    - :envvar:`OTEL_BLRP_MAX_EXPORT_BATCH_SIZE`
    - :envvar:`OTEL_BLRP_EXPORT_TIMEOUT`
    """

    _queue: Deque[LogData]
    _flush_request: Optional[_FlushRequest]
    _log_records: List[Optional[LogData]]

    def __init__(
        self,
        exporter: LogExporter,
        schedule_delay_millis: float = None,
        max_export_batch_size: int = None,
        export_timeout_millis: float = None,
        max_queue_size: int = None,
    ):
        if max_queue_size is None:
            max_queue_size = BatchLogRecordProcessor._default_max_queue_size()

        if schedule_delay_millis is None:
            schedule_delay_millis = (
                BatchLogRecordProcessor._default_schedule_delay_millis()
            )

        if max_export_batch_size is None:
            max_export_batch_size = (
                BatchLogRecordProcessor._default_max_export_batch_size()
            )

        if export_timeout_millis is None:
            export_timeout_millis = (
                BatchLogRecordProcessor._default_export_timeout_millis()
            )

        BatchLogRecordProcessor._validate_arguments(
            max_queue_size, schedule_delay_millis, max_export_batch_size
        )

        self._exporter = exporter
        self._max_queue_size = max_queue_size
        self._schedule_delay_millis = schedule_delay_millis
        self._max_export_batch_size = max_export_batch_size
        self._export_timeout_millis = export_timeout_millis
        self._queue = collections.deque([], max_queue_size)
        self._worker_thread = threading.Thread(
            name="OtelBatchLogRecordProcessor",
            target=self.worker,
            daemon=True,
        )
        self._condition = threading.Condition(threading.Lock())
        self._shutdown = False
        self._flush_request = None
        self._log_records = [None] * self._max_export_batch_size
        self._worker_thread.start()
        if hasattr(os, "register_at_fork"):
            weak_reinit = weakref.WeakMethod(self._at_fork_reinit)
            os.register_at_fork(after_in_child=lambda: weak_reinit()())  # pylint: disable=unnecessary-lambda
        self._pid = os.getpid()

    def _at_fork_reinit(self):
        self._condition = threading.Condition(threading.Lock())
        self._queue.clear()
        self._worker_thread = threading.Thread(
            name="OtelBatchLogRecordProcessor",
            target=self.worker,
            daemon=True,
        )
        self._worker_thread.start()
        self._pid = os.getpid()

    def worker(self):
        timeout = self._schedule_delay_millis / 1e3
        flush_request: Optional[_FlushRequest] = None
        while not self._shutdown:
            with self._condition:
                if self._shutdown:
                    # shutdown may have been called, avoid further processing
                    break
                flush_request = self._get_and_unset_flush_request()
                if (
                    len(self._queue) < self._max_export_batch_size
                    and flush_request is None
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

            start_ns = time_ns()
            self._export(flush_request)
            end_ns = time_ns()
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
        token = attach(set_value(_SUPPRESS_INSTRUMENTATION_KEY, True))
        try:
            self._exporter.export(self._log_records[:idx])  # type: ignore
        except Exception:  # pylint: disable=broad-exception-caught
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
        if self._pid != os.getpid():
            _BSP_RESET_ONCE.do_once(self._at_fork_reinit)

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

    @staticmethod
    def _default_max_queue_size():
        try:
            return int(
                environ.get(OTEL_BLRP_MAX_QUEUE_SIZE, _DEFAULT_MAX_QUEUE_SIZE)
            )
        except ValueError:
            _logger.exception(
                _ENV_VAR_INT_VALUE_ERROR_MESSAGE,
                OTEL_BLRP_MAX_QUEUE_SIZE,
                _DEFAULT_MAX_QUEUE_SIZE,
            )
            return _DEFAULT_MAX_QUEUE_SIZE

    @staticmethod
    def _default_schedule_delay_millis():
        try:
            return int(
                environ.get(
                    OTEL_BLRP_SCHEDULE_DELAY, _DEFAULT_SCHEDULE_DELAY_MILLIS
                )
            )
        except ValueError:
            _logger.exception(
                _ENV_VAR_INT_VALUE_ERROR_MESSAGE,
                OTEL_BLRP_SCHEDULE_DELAY,
                _DEFAULT_SCHEDULE_DELAY_MILLIS,
            )
            return _DEFAULT_SCHEDULE_DELAY_MILLIS

    @staticmethod
    def _default_max_export_batch_size():
        try:
            return int(
                environ.get(
                    OTEL_BLRP_MAX_EXPORT_BATCH_SIZE,
                    _DEFAULT_MAX_EXPORT_BATCH_SIZE,
                )
            )
        except ValueError:
            _logger.exception(
                _ENV_VAR_INT_VALUE_ERROR_MESSAGE,
                OTEL_BLRP_MAX_EXPORT_BATCH_SIZE,
                _DEFAULT_MAX_EXPORT_BATCH_SIZE,
            )
            return _DEFAULT_MAX_EXPORT_BATCH_SIZE

    @staticmethod
    def _default_export_timeout_millis():
        try:
            return int(
                environ.get(
                    OTEL_BLRP_EXPORT_TIMEOUT, _DEFAULT_EXPORT_TIMEOUT_MILLIS
                )
            )
        except ValueError:
            _logger.exception(
                _ENV_VAR_INT_VALUE_ERROR_MESSAGE,
                OTEL_BLRP_EXPORT_TIMEOUT,
                _DEFAULT_EXPORT_TIMEOUT_MILLIS,
            )
            return _DEFAULT_EXPORT_TIMEOUT_MILLIS

    @staticmethod
    def _validate_arguments(
        max_queue_size, schedule_delay_millis, max_export_batch_size
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
                "max_export_batch_size must be less than or equal to max_queue_size."
            )
