# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Configure the OpenTelemetry SDK from a declarative configuration file.

Run an OTLP-capable backend (for example the OpenTelemetry Collector) on
localhost:4318, then run this script to emit a span using the configuration
in ``otel-config.yaml``.
"""

from pathlib import Path

from opentelemetry import trace
from opentelemetry.sdk.configuration import configure_sdk, load_config_file

config_path = Path(__file__).parent / "otel-config.yaml"
configure_sdk(load_config_file(config_path))

tracer = trace.get_tracer("declarative-config-example")

with tracer.start_as_current_span("hello"):
    print("Hello from a declaratively configured SDK!")
