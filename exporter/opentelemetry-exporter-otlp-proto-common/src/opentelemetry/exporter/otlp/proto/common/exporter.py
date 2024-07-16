# Copyright The OpenTelemetry Authors
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

import threading
from contextlib import contextmanager
from logging import getLogger
from time import time
from typing import Callable, Generic, Iterator, Optional, Type, TypeVar

from ._internal import _create_exp_backoff_generator

ExportResultT = TypeVar("ExportResultT", covariant=True)
ExportPayloadT = TypeVar("ExportPayloadT", covariant=True)

_logger = getLogger(__name__)


class RetryableExportError(Exception):
    def __init__(self, retry_delay_sec: Optional[int]):
        super().__init__()
        self.retry_delay_sec = retry_delay_sec


class RetryingExporter(Generic[ExportResultT]):
    """OTLP exporter helper to handle retries and timeouts

    Encapsulates timeout behavior for shutdown and export tasks.

    Accepts a callable `export_function` of the form

        def export_function(
            payload: object,
            timeout_sec: float,
        ) -> result:
            ....

    that either returns the appropriate export result, or raises a RetryableExportError exception if
    the encountered error should be retried.

    Args:
        export_function: A callable handling a single export attempt to be used by
            export_with_retry()
        result: Enum-like type defining SUCCESS and FAILURE values returned by export.
        timeout_sec: Timeout for exports in seconds.
    """

    def __init__(
        self,
        export_function: Callable[[ExportPayloadT, float], ExportResultT],
        result: Type[ExportResultT],
        timeout_sec: float,
    ):
        self._export_function = export_function
        self._result = result
        self._timeout_sec = timeout_sec

        self._shutdown = threading.Event()
        self._export_lock = threading.Lock()

    def shutdown(self, timeout_millis: float = 30_000) -> None:
        """Shutdown the retrying exporter

        Waits for the current export to finish up to `timeout_millis`. In case the timeout is
        reached, the export will be interrupted to to prevent application hanging after completion.
        """
        with acquire_timeout(self._export_lock, timeout_millis / 1e3):
            self._shutdown.set()

    def export_with_retry(  # pylint: disable=too-many-return-statements
        self,
        payload: ExportPayloadT,
        timeout_sec: Optional[float] = None,
    ) -> ExportResultT:
        """Exports payload with handling of retryable errors

        Calls the export_function provided at initialization with the following signature:

            export_function(payload, timeout_sec=remaining_time)

        where `remaining_time` is updated with each retry.

        Retries will be attempted using exponential backoff. If retry_delay_sec is specified in the
        raised error, a retry attempt will not occur before that delay. If a retry after that delay
        is not possible, will immediately abort without retrying.

        In case no timeout_sec is not given, the timeout defaults to the timeout given during
        initialization.

        Will reattempt the export until timeout has passed, at which point the export will be
        abandoned and a failure will be returned. A pending shutdown timing out will also cause
        retries to time out.

        Note: Can block longer than timeout if export_function is blocking. Ensure export_function
            blocks minimally and does not attempt retries.

        Args:
            payload: Data to be exported, which is forwarded to the underlying export
        """
        # After the call to shutdown, subsequent calls to Export are
        # not allowed and should return a Failure result.
        if self._shutdown.is_set():
            _logger.warning("Exporter already shutdown, ignoring batch")
            return self._result.FAILURE

        timeout_sec = (
            timeout_sec if timeout_sec is not None else self._timeout_sec
        )
        deadline_sec = time() + timeout_sec

        # If negative timeout passed (from e.g. external batch deadline - see GRPC metric exporter)
        # fail immediately
        if timeout_sec <= 0:
            _logger.warning("Export deadline passed, ignoring data")
            return self._result.FAILURE

        with acquire_timeout(self._export_lock, timeout_sec) as is_locked:
            if not is_locked:
                _logger.warning(
                    "Exporter failed to acquire lock before timeout"
                )
                return self._result.FAILURE

            max_value = 64
            # expo returns a generator that yields delay values which grow
            # exponentially. Once delay is greater than max_value, the yielded
            # value will remain constant.
            for delay_sec in _create_exp_backoff_generator(
                max_value=max_value
            ):
                remaining_time_sec = deadline_sec - time()
                if remaining_time_sec < 1e-09:
                    return self._result.FAILURE  # Timed out

                if self._shutdown.is_set():
                    _logger.warning(
                        "Export cancelled due to shutdown timing out"
                    )
                    return self._result.FAILURE

                try:
                    return self._export_function(payload, remaining_time_sec)
                except RetryableExportError as exc:
                    time_remaining_sec = deadline_sec - time()

                    delay_sec = (
                        exc.retry_delay_sec
                        if exc.retry_delay_sec is not None
                        else min(time_remaining_sec, delay_sec)
                    )

                    if delay_sec > time_remaining_sec:
                        # We should not exceed the requested timeout
                        return self._result.FAILURE

                    _logger.warning("Retrying in %0.2fs", delay_sec)
                    self._shutdown.wait(delay_sec)

            return self._result.FAILURE


@contextmanager
def acquire_timeout(lock: threading.Lock, timeout: float) -> Iterator[bool]:
    result = lock.acquire(timeout=timeout)
    try:
        yield result
    finally:
        if result:
            lock.release()
