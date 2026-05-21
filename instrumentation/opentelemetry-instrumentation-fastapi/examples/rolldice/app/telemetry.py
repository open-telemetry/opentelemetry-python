# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""OpenTelemetry SDK initialization via declarative (file-based) configuration.

This module loads ``otel-config.yaml`` and uses it as the single source of
truth for the telemetry pipeline configuration.

──────────────────────────────────────────────────────────────────────────────
STATUS: The SDK's file configuration module (opentelemetry-sdk >= 1.41) can
parse and validate the YAML, but the released version does not yet wire up
end-to-end application.  Specifically:

  • load_config_file() returns an OpenTelemetryConfiguration dataclass whose
    nested fields (resource, tracer_provider, etc.) are still raw dicts rather
    than typed model instances.

  • configure_logger_provider() has not been released yet (merged to main in
    PR #4990, 2026-04-13).

  • A top-level configure_sdk(config) orchestrator is proposed in issue #5126
    but not yet implemented.

Once the SDK ships configure_sdk() (or the individual configure_* functions
work with the loader output), this entire file can be reduced to:

    from opentelemetry.sdk._configuration.file import configure_sdk, load_config_file
    config = load_config_file(str(_CONFIG_PATH))
    configure_sdk(config)

Until then, this module parses the YAML for validation and endpoint extraction,
then constructs providers programmatically to match the declared config.

The Python logging bridge (LoggingHandler) is not part of the declarative
config schema and will always require a small programmatic setup step.
──────────────────────────────────────────────────────────────────────────────

Importing this module activates the SDK globally.
"""

import logging
from pathlib import Path

from opentelemetry import _logs, metrics, trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.sdk._configuration.file import load_config_file
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import (
    OTELResourceDetector,
    ProcessResourceDetector,
    Resource,
    SERVICE_NAME,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "otel-config.yaml"


# ──────────────────────────────────────────────────────────────────────────────
# Helpers for extracting values from the parsed config (raw dicts).
# These can be removed once configure_sdk() lands in the SDK.
# ──────────────────────────────────────────────────────────────────────────────


def _build_resource(config) -> Resource:
    """Build a Resource from the parsed config's resource section."""
    service_name = "unknown_service"
    if config.resource and isinstance(config.resource, dict):
        for attr in config.resource.get("attributes", []):
            if attr.get("name") == "service.name":
                service_name = attr["value"]

    base = Resource.create({SERVICE_NAME: service_name})
    process_resource = ProcessResourceDetector().detect()
    otel_resource = OTELResourceDetector().detect()
    return base.merge(process_resource).merge(otel_resource)


def _get_otlp_endpoint(provider_dict, signal_path) -> str | None:
    """Extract the OTLP HTTP endpoint from a provider config dict."""
    if not isinstance(provider_dict, dict):
        return None
    items = provider_dict.get("processors") or provider_dict.get("readers") or []
    for item in items:
        if not isinstance(item, dict):
            continue
        for processor_type in ("batch", "simple", "periodic"):
            proc = item.get(processor_type)
            if not isinstance(proc, dict):
                continue
            exporter = proc.get("exporter", {})
            if isinstance(exporter, dict) and "otlp_http" in exporter:
                otlp = exporter["otlp_http"]
                if isinstance(otlp, dict):
                    return otlp.get("endpoint")
    return None


# ──────────────────────────────────────────────────────────────────────────────


def configure_opentelemetry() -> None:
    """Load otel-config.yaml and install the configured SDK globally.

    Parses and validates the YAML via load_config_file(), then constructs
    providers programmatically using endpoints from the parsed config.
    """
    config = load_config_file(str(_CONFIG_PATH))
    resource = _build_resource(config)

    # ── Traces ──
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    endpoint = _get_otlp_endpoint(config.tracer_provider, "traces")
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
    )
    tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    # ── Metrics ──
    endpoint = _get_otlp_endpoint(config.meter_provider, "metrics")
    metric_readers = [
        PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=endpoint)),
        PeriodicExportingMetricReader(ConsoleMetricExporter()),
    ]
    metrics.set_meter_provider(
        MeterProvider(resource=resource, metric_readers=metric_readers)
    )

    # ── Logs ──
    logger_provider = LoggerProvider(resource=resource)
    _logs.set_logger_provider(logger_provider)

    endpoint = _get_otlp_endpoint(config.logger_provider, "logs")
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(OTLPLogExporter(endpoint=endpoint))
    )
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(ConsoleLogExporter())
    )

    # ── Log bridge (always programmatic — not covered by the config schema) ──
    otel_handler = LoggingHandler(logger_provider=logger_provider)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("%(levelname)s %(name)s - %(message)s")
    )

    root_logger = logging.getLogger()
    root_logger.addHandler(otel_handler)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.DEBUG)


configure_opentelemetry()
