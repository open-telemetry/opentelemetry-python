# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import os
import sys

from opentelemetry.process_context import publish_context, unpublish_context
from opentelemetry.sdk.resources import Resource

first = Resource({"service.name": "otel-first", "version": 1})
second = Resource({"service.name": "otel-second", "version": 2})
publish_context(first)

sys.stdout.write(f"{os.getpid()}\n")
sys.stdout.flush()

for line in sys.stdin:
    match line.strip():
        case "update":
            publish_context(second)
        case "unpublish":
            unpublish_context()
        case "exit":
            break
    sys.stdout.write("done\n")
    sys.stdout.flush()
