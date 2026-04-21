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

from __future__ import annotations

import logging

from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._configuration._common import _parse_headers
from opentelemetry.sdk._configuration._exceptions import ConfigurationError
from opentelemetry.sdk._configuration.models import (
    BatchLogRecordProcessor as BatchLogRecordProcessorConfig,
)
from opentelemetry.sdk._configuration.models import (
    LoggerProvider as LoggerProviderConfig,
)
from opentelemetry.sdk._configuration.models import (
    LogRecordExporter as LogRecordExporterConfig,
)
from opentelemetry.sdk._configuration.models import (
    LogRecordProcessor as LogRecordProcessorConfig,
)
from opentelemetry.sdk._configuration.models import (
    OtlpGrpcExporter as OtlpGrpcExporterConfig,
)
from opentelemetry.sdk._configuration.models import (
    OtlpHttpExporter as OtlpHttpExporterConfig,
)
from opentelemetry.sdk._configuration.models import (
    SimpleLogRecordProcessor as SimpleLogRecordProcessorConfig,
)
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs._internal.export import (
    BatchLogRecordProcessor,
    ConsoleLogRecordExporter,
    LogRecordExporter,
    SimpleLogRecordProcessor,
)
from opentelemetry.sdk.resources import Resource

_logger = logging.getLogger(__name__)

# BatchLogRecordProcessor defaults per OTel spec (milliseconds).
_DEFAULT_SCHEDULE_DELAY_MILLIS = 1000
_DEFAULT_EXPORT_TIMEOUT_MILLIS = 30000
_DEFAULT_MAX_QUEUE_SIZE = 2048
_DEFAULT_MAX_EXPORT_BATCH_SIZE = 512


def _map_compression(
    value: str | None, compression_enum: type
) -> object | None:
    """Map a compression string to the given Compression enum value."""
    if value is None or value.lower() == "none":
        return None
    if value.lower() == "gzip":
        return compression_enum.Gzip  # type: ignore[attr-defined]
    raise ConfigurationError(
        f"Unsupported compression value '{value}'. Supported values: 'gzip', 'none'."
    )


def _create_console_log_exporter() -> ConsoleLogRecordExporter:
    """Create a ConsoleLogRecordExporter."""
    return ConsoleLogRecordExporter()


def _create_otlp_http_log_exporter(
    config: OtlpHttpExporterConfig,
) -> LogRecordExporter:
    """Create an OTLP HTTP log exporter from config."""
    try:
        # pylint: disable=import-outside-toplevel,no-name-in-module
        from opentelemetry.exporter.otlp.proto.http import (  # type: ignore[import-untyped]  # noqa: PLC0415
            Compression,
        )
        from opentelemetry.exporter.otlp.proto.http._log_exporter import (  # type: ignore[import-untyped]  # noqa: PLC0415
            OTLPLogExporter,
        )
    except ImportError as exc:
        raise ConfigurationError(
            "otlp_http log exporter requires 'opentelemetry-exporter-otlp-proto-http'. "
            "Install it with: pip install opentelemetry-exporter-otlp-proto-http"
        ) from exc

    compression = _map_compression(config.compression, Compression)
    headers = _parse_headers(config.headers, config.headers_list)
    timeout = (config.timeout / 1000.0) if config.timeout is not None else None

    return OTLPLogExporter(  # type: ignore[return-value]
        endpoint=config.endpoint,
        headers=headers,
        timeout=timeout,
        compression=compression,  # type: ignore[arg-type]
    )


def _create_otlp_grpc_log_exporter(
    config: OtlpGrpcExporterConfig,
) -> LogRecordExporter:
    """Create an OTLP gRPC log exporter from config."""
    try:
        # pylint: disable=import-outside-toplevel,no-name-in-module
        import grpc  # type: ignore[import-untyped]  # noqa: PLC0415

        from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (  # type: ignore[import-untyped]  # noqa: PLC0415
            OTLPLogExporter,
        )
    except ImportError as exc:
        raise ConfigurationError(
            "otlp_grpc log exporter requires 'opentelemetry-exporter-otlp-proto-grpc'. "
            "Install it with: pip install opentelemetry-exporter-otlp-proto-grpc"
        ) from exc

    compression = _map_compression(config.compression, grpc.Compression)
    headers = _parse_headers(config.headers, config.headers_list)
    timeout = (config.timeout / 1000.0) if config.timeout is not None else None

    return OTLPLogExporter(  # type: ignore[return-value]
        endpoint=config.endpoint,
        headers=headers,
        timeout=timeout,
        compression=compression,  # type: ignore[arg-type]
    )


def _create_log_record_exporter(
    config: LogRecordExporterConfig,
) -> LogRecordExporter:
    """Create a log record exporter from config."""
    if config.console is not None:
        return _create_console_log_exporter()
    if config.otlp_http is not None:
        return _create_otlp_http_log_exporter(config.otlp_http)
    if config.otlp_grpc is not None:
        return _create_otlp_grpc_log_exporter(config.otlp_grpc)
    if config.otlp_file_development is not None:
        raise ConfigurationError(
            "otlp_file_development log exporter is experimental and not yet supported."
        )
    raise ConfigurationError(
        "No exporter type specified in log record exporter config. "
        "Supported types: console, otlp_http, otlp_grpc."
    )


def _create_batch_log_record_processor(
    config: BatchLogRecordProcessorConfig,
) -> BatchLogRecordProcessor:
    """Create a BatchLogRecordProcessor from config.

    Passes explicit defaults to suppress OTEL_BLRP_* env var reading.
    """
    exporter = _create_log_record_exporter(config.exporter)
    schedule_delay = (
        config.schedule_delay
        if config.schedule_delay is not None
        else _DEFAULT_SCHEDULE_DELAY_MILLIS
    )
    export_timeout = (
        config.export_timeout
        if config.export_timeout is not None
        else _DEFAULT_EXPORT_TIMEOUT_MILLIS
    )
    max_queue_size = (
        config.max_queue_size
        if config.max_queue_size is not None
        else _DEFAULT_MAX_QUEUE_SIZE
    )
    max_export_batch_size = (
        config.max_export_batch_size
        if config.max_export_batch_size is not None
        else _DEFAULT_MAX_EXPORT_BATCH_SIZE
    )
    return BatchLogRecordProcessor(
        exporter=exporter,
        schedule_delay_millis=float(schedule_delay),
        export_timeout_millis=float(export_timeout),
        max_queue_size=max_queue_size,
        max_export_batch_size=max_export_batch_size,
    )


def _create_simple_log_record_processor(
    config: SimpleLogRecordProcessorConfig,
) -> SimpleLogRecordProcessor:
    """Create a SimpleLogRecordProcessor from config."""
    exporter = _create_log_record_exporter(config.exporter)
    return SimpleLogRecordProcessor(exporter)


def _create_log_record_processor(
    config: LogRecordProcessorConfig,
) -> BatchLogRecordProcessor | SimpleLogRecordProcessor:
    """Create a log record processor from config."""
    if config.batch is not None:
        return _create_batch_log_record_processor(config.batch)
    if config.simple is not None:
        return _create_simple_log_record_processor(config.simple)
    raise ConfigurationError(
        "No processor type specified in log record processor config. "
        "Supported types: batch, simple."
    )


def create_logger_provider(
    config: LoggerProviderConfig | None,
    resource: Resource | None = None,
) -> LoggerProvider:
    """Create an SDK LoggerProvider from declarative config.

    Does NOT read OTEL_BLRP_* or other env vars for values explicitly
    controlled by the config. Absent config values use OTel spec defaults.

    Args:
        config: LoggerProvider config from the parsed config file, or None.
        resource: Resource to attach to the provider.

    Returns:
        A configured LoggerProvider.
    """
    provider = LoggerProvider(resource=resource)

    if config is None:
        return provider

    if config.limits is not None:
        _logger.warning(
            "log_record_limits are specified in config but are not supported "
            "by the Python SDK LoggerProvider constructor; limits will be ignored."
        )

    for processor_config in config.processors:
        provider.add_log_record_processor(
            _create_log_record_processor(processor_config)
        )

    return provider


def configure_logger_provider(
    config: LoggerProviderConfig | None,
    resource: Resource | None = None,
) -> None:
    """Configure the global LoggerProvider from declarative config.

    When config is None (logger_provider section absent from config file),
    the global is not set — matching Java/JS SDK behavior.

    Args:
        config: LoggerProvider config from the parsed config file, or None.
        resource: Resource to attach to the provider.
    """
    if config is None:
        return
    set_logger_provider(create_logger_provider(config, resource))
