# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import json
import os

from opentelemetry._logs import LogRecord
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs._internal import (
    ConcurrentMultiLogRecordProcessor,
    LogRecordProcessor,
)


class RecordingLogRecordProcessor(LogRecordProcessor):
    def __init__(self) -> None:
        self.bodies: list[str] = []

    def on_emit(self, log_record) -> None:
        self.bodies.append(log_record.log_record.body)

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


def main() -> None:
    processor = RecordingLogRecordProcessor()
    logger_provider = LoggerProvider(
        multi_log_record_processor=ConcurrentMultiLogRecordProcessor(),
        shutdown_on_exit=False,
    )
    logger_provider.add_log_record_processor(processor)
    logger = logger_provider.get_logger("fork")

    # The executor only starts its worker threads on first use, so the
    # inherited state this guards against exists only after an emit.
    logger.emit(LogRecord(observed_timestamp=0, body="parent"))
    parent_pid = os.getpid()

    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if not pid:
        os.close(read_fd)
        # Without a fresh executor in the child this emit never returns: the
        # inherited idle semaphore reports a worker as available, so no thread
        # is started and the submitted call is never run.
        logger.emit(LogRecord(observed_timestamp=0, body="child"))
        with os.fdopen(write_fd, "w") as child_out:
            json.dump(
                {"child_pid": os.getpid(), "child_bodies": processor.bodies},
                child_out,
                sort_keys=True,
            )
        os._exit(0)

    # A pipe rather than the shared stdout, so the two processes' output
    # cannot interleave.
    os.close(write_fd)
    with os.fdopen(read_fd) as child_in:
        child_payload = child_in.read()
    _, status = os.waitpid(pid, 0)
    logger.emit(LogRecord(observed_timestamp=0, body="parent after fork"))
    print(
        json.dumps(
            {
                "parent_pid": parent_pid,
                "child_status": status,
                "child_payload": child_payload,
                "parent_bodies": processor.bodies,
            },
            sort_keys=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
