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
from logging import getLogger
from time import sleep
from typing import Callable, Generic, Optional, Type, TypeVar

from ._internal import _create_exp_backoff_generator

ExportResultT = TypeVar("ExportResultT", covariant=True)
ExportPayloadT = TypeVar("ExportPayloadT", covariant=True)

_logger = getLogger(__name__)


class RetryableExportError(Exception):
    def __init__(self, retry_delay_sec: Optional[int]):
        super().__init__()
        self.retry_delay_sec = retry_delay_sec


class RetryingExporter(Generic[ExportResultT]):
    def __init__(
        self,
        export_function: Callable[[ExportPayloadT, float], ExportResultT],
        result: Type[ExportResultT],
        timeout_sec: float,
    ):
        self._export_function = export_function
        self._result = result
        self._timeout_sec = timeout_sec

        self._shutdown = False
        self._export_lock = threading.Lock()

    def shutdown(self, timeout_millis: float = 30_000) -> None:
        # wait for the last export if any
        self._export_lock.acquire(  # pylint: disable=consider-using-with
            timeout=timeout_millis / 1e3
        )
        self._shutdown = True
        self._export_lock.release()

    def export_with_retry(self, payload: ExportPayloadT) -> ExportResultT:
        # After the call to shutdown, subsequent calls to Export are
        # not allowed and should return a Failure result.
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring batch")
            return self._result.FAILURE

        max_value = 64
        # expo returns a generator that yields delay values which grow
        # exponentially. Once delay is greater than max_value, the yielded
        # value will remain constant.
        for delay in _create_exp_backoff_generator(max_value=max_value):
            if delay == max_value or self._shutdown:
                return self._result.FAILURE

            with self._export_lock:
                try:
                    return self._export_function(payload, self._timeout_sec)
                except RetryableExportError as exc:
                    delay_sec = (
                        exc.retry_delay_sec
                        if exc.retry_delay_sec is not None
                        else delay
                    )
                    _logger.warning("Retrying in %ss", delay_sec)
                    sleep(delay_sec)

        return self._result.FAILURE
