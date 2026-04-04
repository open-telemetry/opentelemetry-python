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

import threading
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from unittest.mock import MagicMock, patch


def _build_mock_response(status: int) -> MagicMock:
    resp = MagicMock()
    resp.status = status
    return resp


@contextmanager
def mock_clock(
    start: float = 0.0,
) -> Generator[Callable[[], float], None, None]:
    """Context manager replacing wall-clock and blocking primitives with a mock clock.

    Args:
        start: Initial clock value (default 0.0).

    Yields:
        A zero-argument callable that returns the current mock time.
    """
    _clock: list[float] = [start]

    def _now() -> float:
        return _clock[0]

    def _sleep(seconds: float) -> None:
        _clock[0] += seconds

    def _event_wait(
        self: threading.Event, timeout: float | None = None
    ) -> bool:
        if self.is_set():
            return True
        if timeout is not None:
            _clock[0] += timeout
        return False

    with (
        patch(
            "opentelemetry.exporter.otlp.json.http._internal.time.time",
            new=_now,
        ),
        patch("time.sleep", new=_sleep),
        patch.object(threading.Event, "wait", _event_wait),
    ):
        yield _now


class CountdownEvent:
    """A threading.Event-like stub that signals after a fixed number of wait() calls.

    Each call to wait() that has not yet reached the trigger count advances the mock
    clock via time.sleep(), integrating naturally with mock_clock().  On the trigger
    call, wait() returns True immediately without sleeping, simulating an external
    shutdown signal interrupting a retry backoff loop.
    """

    def __init__(self, trigger_after: int) -> None:
        self._calls = 0
        self._trigger_after = trigger_after

    def wait(self, timeout: float | None = None) -> bool:
        self._calls += 1
        if self._calls >= self._trigger_after:
            return True
        if timeout is not None:
            time.sleep(timeout)
        return False

    def set(self) -> None:
        pass

    def is_set(self) -> bool:
        return False
