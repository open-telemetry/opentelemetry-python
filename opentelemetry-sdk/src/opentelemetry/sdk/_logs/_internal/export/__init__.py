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
from __future__ import annotations

import abc
import collections
import enum
import logging
import os
import sys
import threading
import weakref
from os import environ, linesep
from typing import IO, Callable, Deque, Optional, Sequence

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


class BatchLogExportStrategy(enum.Enum):
    EXPORT_ALL = 0
    EXPORT_WHILE_BATCH_EXCEEDS_THRESHOLD = 1
    EXPORT_AT_LEAST_ONE_BATCH = 2


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

    def __init__(
        self,
        exporter: LogExporter,
        schedule_delay_millis: float | None = None,
        max_export_batch_size: int | None = None,
        export_timeout_millis: float | None = None,
        max_queue_size: int | None = None,
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
        # Not used. No way currently to pass timeout to export.
        if export_timeout_millis is None:
            export_timeout_millis = (
                BatchLogRecordProcessor._default_export_timeout_millis()
            )

        BatchLogRecordProcessor._validate_arguments(
            max_queue_size, schedule_delay_millis, max_export_batch_size
        )

        self._exporter = exporter
        self._max_queue_size = max_queue_size
        self._schedule_delay = schedule_delay_millis / 1e3
        self._max_export_batch_size = max_export_batch_size
        # Not used. No way currently to pass timeout to export.
        # TODO(https://github.com/open-telemetry/opentelemetry-python/issues/4555): figure out what this should do.
        self._export_timeout_millis = export_timeout_millis
        # Deque is thread safe.
        self._queue = collections.deque([], max_queue_size)
        self._worker_thread = threading.Thread(
            name="OtelBatchLogRecordProcessor",
            target=self.worker,
            daemon=True,
        )

        self._shutdown = False
        self._export_lock = threading.Lock()
        self._worker_awaken = threading.Event()
        self._worker_thread.start()
        if hasattr(os, "register_at_fork"):
            weak_reinit = weakref.WeakMethod(self._at_fork_reinit)
            os.register_at_fork(after_in_child=lambda: weak_reinit()())  # pylint: disable=unnecessary-lambda
        self._pid = os.getpid()

    def _should_export_batch(
        self, batch_strategy: BatchLogExportStrategy, num_iterations: int
    ) -> bool:
        if not self._queue:
            return False
        # Always continue to export while queue length exceeds max batch size.
        if len(self._queue) >= self._max_export_batch_size:
            return True
        if batch_strategy is BatchLogExportStrategy.EXPORT_ALL:
            return True
        if batch_strategy is BatchLogExportStrategy.EXPORT_AT_LEAST_ONE_BATCH:
            return num_iterations == 0
        return False

    def _at_fork_reinit(self):
        self._export_lock = threading.Lock()
        self._worker_awaken = threading.Event()
        self._queue.clear()
        self._worker_thread = threading.Thread(
            name="OtelBatchLogRecordProcessor",
            target=self.worker,
            daemon=True,
        )
        self._worker_thread.start()
        self._pid = os.getpid()

    def worker(self):
        while not self._shutdown:
            # Lots of strategies in the spec for setting next timeout.
            # https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/trace/sdk.md#batching-processor.
            # Shutdown will interrupt this sleep. Emit will interrupt this sleep only if the queue is bigger then threshold.
            sleep_interrupted = self._worker_awaken.wait(self._schedule_delay)
            if self._shutdown:
                break
            self._export(
                BatchLogExportStrategy.EXPORT_WHILE_BATCH_EXCEEDS_THRESHOLD
                if sleep_interrupted
                else BatchLogExportStrategy.EXPORT_AT_LEAST_ONE_BATCH
            )
            self._worker_awaken.clear()
        self._export(BatchLogExportStrategy.EXPORT_ALL)

    def _export(self, batch_strategy: BatchLogExportStrategy) -> None:
        with self._export_lock:
            iteration = 0
            # We could see concurrent export calls from worker and force_flush. We call _should_export_batch
            # once the lock is obtained to see if we still need to make the requested export.
            while self._should_export_batch(batch_strategy, iteration):
                iteration += 1
                token = attach(set_value(_SUPPRESS_INSTRUMENTATION_KEY, True))
                try:
                    self._exporter.export(
                        [
                            # Oldest records are at the back, so pop from there.
                            self._queue.pop()
                            for _ in range(
                                min(
                                    self._max_export_batch_size,
                                    len(self._queue),
                                )
                            )
                        ]
                    )
                except Exception:  # pylint: disable=broad-exception-caught
                    _logger.exception("Exception while exporting logs.")
                detach(token)

    # Do not add any logging.log statements to this function, they can be being routed back to this `emit` function,
    # resulting in endless recursive calls that crash the program.
    # See https://github.com/open-telemetry/opentelemetry-python/issues/4261
    def emit(self, log_data: LogData) -> None:
        if self._shutdown:
            return
        if self._pid != os.getpid():
            _BSP_RESET_ONCE.do_once(self._at_fork_reinit)

        # This will drop a log from the right side if the queue is at _max_queue_length.
        self._queue.appendleft(log_data)
        if len(self._queue) >= self._max_export_batch_size:
            self._worker_awaken.set()

    def shutdown(self):
        if self._shutdown:
            return
        # Prevents emit and force_flush from further calling export.
        self._shutdown = True
        # Interrupts sleep in the worker, if it's sleeping.
        self._worker_awaken.set()
        # Main worker loop should exit after one final export call with flush all strategy.
        self._worker_thread.join()
        self._exporter.shutdown()

    def force_flush(self, timeout_millis: Optional[int] = None) -> bool:
        if self._shutdown:
            return
        # Blocking call to export.
        self._export(BatchLogExportStrategy.EXPORT_ALL)

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
