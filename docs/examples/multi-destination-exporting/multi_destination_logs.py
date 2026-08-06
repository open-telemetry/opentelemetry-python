# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""
This example shows how to export logs to multiple destinations.
Each BatchLogRecordProcessor has its own queue and retry logic, so
destinations do not block each other.
"""

import logging

from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
    OTLPLogExporter as GrpcLogExporter,
)
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
    OTLPLogExporter as HttpLogExporter,
)

# this is available in the opentelemetry-instrumentation-logging package
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import (
    BatchLogRecordProcessor,
    ConsoleLogRecordExporter,
)

logger_provider = LoggerProvider()
set_logger_provider(logger_provider)

# Destination 1: OTLP over gRPC
grpc_exporter = GrpcLogExporter(
    endpoint="http://localhost:4317", insecure=True
)
logger_provider.add_log_record_processor(
    BatchLogRecordProcessor(grpc_exporter)
)

# Destination 2: OTLP over HTTP
http_exporter = HttpLogExporter(endpoint="http://localhost:4318/v1/logs")
logger_provider.add_log_record_processor(
    BatchLogRecordProcessor(http_exporter)
)

# Destination 3: Console (for debugging)
logger_provider.add_log_record_processor(
    BatchLogRecordProcessor(ConsoleLogRecordExporter())
)

# Bridge Python's logging to OpenTelemetry
handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
logging.getLogger().setLevel(logging.NOTSET)
logging.getLogger().addHandler(handler)

logger = logging.getLogger("myapp")
logger.info("Logs are exported to all three destinations.")
logger.warning("This warning also goes everywhere.")

logger_provider.shutdown()
