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

    pid = os.fork()
    if not pid:
        child_pid = os.getpid()
        new_logger = logger_provider.get_logger("new")
        logger.emit(LogRecord(observed_timestamp=0, body="cached"))
        new_logger.emit(LogRecord(observed_timestamp=0, body="new"))
        finished_logs = exporter.get_finished_logs()
        print(
            json.dumps(
                {
                    "child_pid": child_pid,
                    "provider_pid": logger_provider.resource.attributes[
                        PROCESS_PID
                    ],
                    "cached_logger_pid": logger.resource.attributes[
                        PROCESS_PID
                    ],
                    "new_logger_pid": new_logger.resource.attributes[
                        PROCESS_PID
                    ],
                    "exported_resource_pids": [
                        log.resource.attributes[PROCESS_PID]
                        for log in finished_logs
                    ],
                    "log_bodies": sorted(
                        log.log_record.body for log in finished_logs
                    ),
                }
            ),
            flush=True,
        )
        # pylint: disable-next=protected-access
        os._exit(0)

    os.waitpid(pid, 0)
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
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
