# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import json
import os

from opentelemetry._logs import LogRecord
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import (
    InMemoryLogRecordExporter,
    SimpleLogRecordProcessor,
)
from opentelemetry.sdk.resources import PROCESS_PID


# pylint: disable-next=too-many-locals
def main() -> None:
    exporter = InMemoryLogRecordExporter()
    logger_provider = LoggerProvider(shutdown_on_exit=False)
    logger_provider.add_log_record_processor(
        SimpleLogRecordProcessor(exporter)
    )
    logger = logger_provider.get_logger("cached")
    parent_pid = os.getpid()
    parent_resource_pid = logger_provider.resource.attributes[PROCESS_PID]
    parent_logger_pid = logger.resource.attributes[PROCESS_PID]

    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if not pid:
        os.close(read_fd)
        child_pid = os.getpid()
        new_logger = logger_provider.get_logger("new")
        logger.emit(LogRecord(observed_timestamp=0, body="cached"))
        new_logger.emit(LogRecord(observed_timestamp=0, body="new"))
        finished_logs = exporter.get_finished_logs()
        payload = {
            "child_pid": child_pid,
            "provider_pid": logger_provider.resource.attributes[PROCESS_PID],
            "cached_logger_pid": logger.resource.attributes[PROCESS_PID],
            "new_logger_pid": new_logger.resource.attributes[PROCESS_PID],
            "exported_resource_pids": [
                log.resource.attributes[PROCESS_PID] for log in finished_logs
            ],
            "log_bodies": sorted(
                log.log_record.body for log in finished_logs
            ),
        }
        os.write(write_fd, json.dumps(payload).encode())
        os.close(write_fd)
        # pylint: disable-next=protected-access
        os._exit(0)

    os.close(write_fd)
    child_payload = os.read(read_fd, 4096)
    os.close(read_fd)
    _, status = os.waitpid(pid, 0)
    exit_code = os.waitstatus_to_exitcode(status)
    if exit_code != 0:
        raise SystemExit(exit_code)

    print(
        json.dumps(
            {
                "parent_pid": parent_pid,
                "parent_resource_pid": parent_resource_pid,
                "parent_logger_pid": parent_logger_pid,
                "parent_resource_pid_after_fork": logger_provider.resource.attributes[
                    PROCESS_PID
                ],
                "parent_logger_pid_after_fork": logger.resource.attributes[
                    PROCESS_PID
                ],
                "child": json.loads(child_payload.decode()),
            }
        ),
        flush=True
    )


if __name__ == "__main__":
    main()
