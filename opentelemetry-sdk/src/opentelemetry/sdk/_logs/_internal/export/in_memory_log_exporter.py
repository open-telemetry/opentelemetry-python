# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
"""Log record exporter that keeps everything in a list.

Written for tests: register the exporter on a processor, run the code under
test, then read back the records it produced.

It sits in a module of its own rather than in
``opentelemetry.sdk._logs._internal.export`` because it imports the public
``opentelemetry.sdk._logs.export``, which imports that private module.
``opentelemetry.sdk._logs.export`` therefore re-exports it from here directly.
"""

import collections.abc
import threading

from typing_extensions import deprecated

from opentelemetry.sdk._logs import ReadableLogRecord
from opentelemetry.sdk._logs.export import (
    LogRecordExporter,
    LogRecordExportResult,
)


class InMemoryLogRecordExporter(LogRecordExporter):
    """Implementation of :class:`.LogRecordExporter` that stores logs in memory.

    This class can be used for testing purposes. It stores the exported logs
    in a list in memory that can be retrieved using the
    :meth:`.get_finished_logs` method.

    Records accumulate until ``clear`` is called, so a long-running test leaks
    memory in proportion to how much it logs. The stored records are the ones
    the processor handed over, not copies, so mutating one afterwards changes
    what a later read returns.
    """

    def __init__(self) -> None:
        """Build the exporter with an empty, not yet shut down, store."""
        self._logs = []
        self._lock = threading.Lock()
        self._stopped = False

    def clear(self) -> None:
        """Discard every record collected so far.

        Useful between phases of one test. It does not reset the shutdown flag,
        so an exporter that was shut down keeps rejecting exports after this.
        """
        with self._lock:
            self._logs.clear()

    def get_finished_logs(self) -> tuple[ReadableLogRecord, ...]:
        """Read back the records collected so far.

        Call ``force_flush`` on the processor first when a
        ``BatchLogRecordProcessor`` is in use, since a record still sitting in
        its queue has not reached this exporter yet.

        Returns:
            The records in the order they were exported, oldest first. The
            tuple is a snapshot, so a later export does not grow it, but the
            records inside it are shared with the exporter.
        """
        with self._lock:
            return tuple(self._logs)

    def export(self, batch: collections.abc.Sequence[ReadableLogRecord]) -> LogRecordExportResult:
        """Append a batch of records to the store.

        Args:
            batch: The records to store. They are appended in the order given.

        Returns:
            ``LogRecordExportResult.FAILURE`` when ``shutdown`` has been
            called, in which case the batch is discarded.
            ``LogRecordExportResult.SUCCESS`` otherwise.
        """
        if self._stopped:
            return LogRecordExportResult.FAILURE
        with self._lock:
            self._logs.extend(batch)
        return LogRecordExportResult.SUCCESS

    def shutdown(self) -> None:
        """Make every later export fail.

        Records already collected stay readable through
        ``get_finished_logs``, which is what lets a test assert on them after
        shutting the SDK down. The call is idempotent.
        """
        self._stopped = True

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Do nothing, since export is already synchronous.

        Args:
            timeout_millis: Ignored. Accepted so that the signature matches
                ``LogRecordExporter``.

        Returns:
            ``True``, always.
        """
        return True


@deprecated("Use InMemoryLogRecordExporter. Since logs are not stable yet this WILL be removed in future releases.")
class InMemoryLogExporter(InMemoryLogRecordExporter):
    """Deprecated alias of ``InMemoryLogRecordExporter``.

    Behaves identically. Instantiating it emits a ``DeprecationWarning``, and
    type checkers report its use.
    """
