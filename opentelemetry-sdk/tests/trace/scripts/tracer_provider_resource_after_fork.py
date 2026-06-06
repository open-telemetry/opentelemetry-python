# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import json
import os

from opentelemetry.sdk import trace
from opentelemetry.sdk.resources import PROCESS_PID


def main() -> None:
    tracer_provider = trace.TracerProvider(shutdown_on_exit=False)
    tracer = tracer_provider.get_tracer("cached")
    parent_pid = os.getpid()
    parent_resource_pid = tracer_provider.resource.attributes[PROCESS_PID]
    parent_tracer_pid = tracer.resource.attributes[PROCESS_PID]

    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if not pid:
        os.close(read_fd)
        child_pid = os.getpid()
        new_tracer = tracer_provider.get_tracer("new")
        span = tracer.start_span("child")
        payload = {
            "child_pid": child_pid,
            "provider_pid": tracer_provider.resource.attributes[PROCESS_PID],
            "cached_tracer_pid": tracer.resource.attributes[PROCESS_PID],
            "new_tracer_pid": new_tracer.resource.attributes[PROCESS_PID],
            "span_pid": span.resource.attributes[PROCESS_PID],
        }
        os.write(write_fd, json.dumps(payload).encode())
        os.close(write_fd)
        # pylint: disable-next=protected-access
        os._exit(0)

    os.close(write_fd)
    child_payload = os.read(read_fd, 4096)
    os.close(read_fd)
    _, status = os.waitpid(pid, 0)
    if status != 0:
        raise SystemExit(status)

    print(
        json.dumps(
            {
                "parent_pid": parent_pid,
                "parent_resource_pid": parent_resource_pid,
                "parent_tracer_pid": parent_tracer_pid,
                "parent_resource_pid_after_fork": tracer_provider.resource.attributes[
                    PROCESS_PID
                ],
                "parent_tracer_pid_after_fork": tracer.resource.attributes[
                    PROCESS_PID
                ],
                "child": json.loads(child_payload.decode()),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
