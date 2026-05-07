# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import opentelemetry.trace


def dummy_check_mypy_returntype() -> opentelemetry.trace.TracerProvider:
    return opentelemetry.trace.get_tracer_provider()
