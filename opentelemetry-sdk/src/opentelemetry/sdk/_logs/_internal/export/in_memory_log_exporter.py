# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

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
    """

    def __init__(self) -> None:
        self._logs = []
        self._lock = threading.Lock()
        self._stopped = False

    def clear(self) -> None:
        """Discard every record collected so far."""
        with self._lock:
            self._logs.clear()

    def get_finished_logs(self) -> tuple[ReadableLogRecord, ...]:
        """Read back the records collected so far.

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
        """Make every later export fail."""
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
    """Deprecated alias of ``InMemoryLogRecordExporter``."""
