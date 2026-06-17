# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import sys
import threading
from collections.abc import Callable
from os import PathLike
from typing import IO, Generic, Literal, TypeVar

_logger = logging.getLogger(__name__)

T = TypeVar("T")


class _FileExporter(Generic[T]):
    def __init__(
        self,
        encode: Callable[[T], dict | None],
        kind: Literal["spans", "logs", "metrics"],
        logger: logging.Logger | None = None,
        path: str | PathLike[str] | None = None,
        stream: IO[str] | None = None,
    ) -> None:
        if path is not None and stream is not None:
            raise ValueError("Cannot specify both 'path' and 'stream'")
        if path is not None:
            self._stream: IO[str] = open(  # pylint: disable=consider-using-with
                path, "a", encoding="utf-8"
            )
            self._owns_stream = True
        elif stream is not None:
            self._stream = stream
            self._owns_stream = False
        else:
            self._stream = sys.stdout
            self._owns_stream = False
        self._shutdown = False
        self._encode = encode
        self._kind = kind
        self._logger = logger if logger is not None else _logger
        self._lock = threading.Lock()

    def export(self, data: T) -> bool:
        if self._shutdown:
            self._logger.warning("Exporter already shutdown, ignoring call")
            return False
        try:
            encoded = self._encode(data)
            with self._lock:
                if self._stream.closed:
                    self._logger.warning(
                        "Stream is closed, ignoring %s export call", self._kind
                    )
                    return False
                if encoded is not None:
                    self._stream.write(_format_line(encoded))
                self._stream.flush()
        # pylint: disable-next=broad-exception-caught
        except Exception as error:
            self._logger.exception(
                "Failed to write %s batch to stream: %s: %s",
                self._kind,
                type(error).__name__,
                error,
            )
            return False
        return True

    def shutdown(self) -> None:
        if self._shutdown:
            self._logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        if self._owns_stream:
            with self._lock:
                self._stream.close()


def _format_line(entry: dict) -> str:
    return json.dumps(entry, separators=(",", ":")) + "\n"
