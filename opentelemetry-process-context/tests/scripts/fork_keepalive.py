# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access

import os
import signal
import sys

from opentelemetry.process_context import publish_context
from opentelemetry.sdk.resources import Resource

resource = Resource({"service.name": "otel-test-service", "version": 42})
publish_context(resource)

pid = os.fork()
if not pid:
    # Child: do not publish, block until the parent kills us.
    signal.pause()
    os._exit(0)

sys.stdout.write(f"{os.getpid()} {pid}\n")
sys.stdout.flush()
sys.stdin.readline()
os.kill(pid, signal.SIGKILL)
os.waitpid(pid, 0)
os._exit(0)
