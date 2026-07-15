# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from unittest.mock import Mock, patch


@contextmanager
def _mock_clock(
    shutdown_event: Mock | None = None,
) -> Iterator[Callable[[float], None]]:
    _now = 0.0

    def advance(delta: float) -> None:
        nonlocal _now
        _now += delta

    def get_time() -> float:
        return _now

    if shutdown_event is not None:

        def _wait(duration: float) -> bool:
            advance(duration)
            return False

        shutdown_event.wait.side_effect = _wait

    with patch(
        "opentelemetry.exporter.otlp.common._http.time.time",
        side_effect=get_time,
    ):
        yield advance
