# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""A minimal application driven by declarative configuration.

The SDK is configured entirely from ``otel-config.yaml`` via the
``OTEL_CONFIG_FILE`` environment variable. Run with
``opentelemetry-instrument`` so the configurator picks up the env var:

    OTEL_CONFIG_FILE=$(pwd)/otel-config.yaml opentelemetry-instrument python app.py
"""

from opentelemetry import trace

tracer = trace.get_tracer("declarative-config-example")

with tracer.start_as_current_span("hello"):
    print("Hello from a declaratively configured SDK!")
