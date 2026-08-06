# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import sys

from opentelemetry.process_context import publish_context
from opentelemetry.sdk.resources import Resource

resource = Resource({"service.name": "otel-test-service", "version": 42})
publish_context(resource, {"deployment.environment": "otel-test-env"})

sys.stdout.write("ready\n")
sys.stdout.flush()
sys.stdin.readline()
