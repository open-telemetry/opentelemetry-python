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
import threading
from abc import ABC
from typing import (
    Deque,
    Optional,
    Union,
    Sequence
)

from opentelemetry.context import (
    _SUPPRESS_INSTRUMENTATION_KEY,
    attach,
    detach,
    set_value,
)
from opentelemetry.sdk._logs import LogRecord
from opentelemetry.sdk._logs.export import LogExporter
from opentelemetry.sdk.trace import Span
from opentelemetry.sdk.trace.export import SpanExporter
from opentelemetry.util._once import Once

from opentelemetry.context import (
    _SUPPRESS_INSTRUMENTATION_KEY,
    attach,
    detach,
    set_value,
)
from opentelemetry.sdk._logs import LogData,


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

class BatchExportStrategy(enum.Enum):
    EXPORT_ALL = 0
    EXPORT_WHILE_BATCH_EXCEEDS_THRESHOLD = 1
    EXPORT_AT_LEAST_ONE_BATCH = 2


class BatchProcessor(ABC):
    _queue: Deque[Union[LogRecord | Span]]

    def __init__(
        self,
        exporter: Union[LogExporter | SpanExporter],
        schedule_delay_millis: float,
        max_export_batch_size: int,
        export_timeout_millis: float,
        max_queue_size: int,
        exporting: str,
    ):
        self._bsp_reset_once = Once()
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
            name="OtelBatch{}RecordProcessor".format(exporting),
            target=self.worker,
            daemon=True,
        )
        self._logger = logging.getLogger(__name__)
        self._exporting = exporting

        self._shutdown = False
        self._export_lock = threading.Lock()
        self._worker_awaken = threading.Event()
        self._worker_thread.start()
        if hasattr(os, "register_at_fork"):
            os.register_at_fork(after_in_child=self._at_fork_reinit)  # pylint: disable=protected-access
        self._pid = os.getpid()

    def _should_export_batch(
        self, batch_strategy: BatchExportStrategy, num_iterations: int
    ) -> bool:
        if not self._queue:
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
        self._export_lock = threading.Lock()
        self._worker_awaken = threading.Event()
        self._queue.clear()
        self._worker_thread = threading.Thread(
            name="OtelBatch{}RecordProcessor".format(self._exporting),
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
                BatchExportStrategy.EXPORT_WHILE_BATCH_EXCEEDS_THRESHOLD
                if sleep_interrupted
                else BatchExportStrategy.EXPORT_AT_LEAST_ONE_BATCH
            )
            self._worker_awaken.clear()
        self._export(BatchExportStrategy.EXPORT_ALL)

    def _export(self, batch_strategy: BatchExportStrategy) -> None:
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
                    self._logger.exception(
                        "Exception while exporting {}.".format(self._exporting)
                    )
                detach(token)

    def emit(self, data: Union[LogRecord | Span]) -> None:
        if self._shutdown:
            self._logger.info(
                "Shutdown called, ignoring {}.".format(self._exporting)
            )
            return
        if self._pid != os.getpid():
            self.bsp_reset_once.do_once(self._at_fork_reinit)

        if len(self._queue) == self._max_queue_size:
            self._logger.warning(
                "Queue full, dropping {}.".format(self._exporting)
            )
        self._queue.appendleft(data)
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
        self._export(BatchExportStrategy.EXPORT_ALL)