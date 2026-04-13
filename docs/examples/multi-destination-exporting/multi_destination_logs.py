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
http_exporter = HttpLogExporter(
    endpoint="http://localhost:4318/v1/logs"
)
logger_provider.add_log_record_processor(
    BatchLogRecordProcessor(http_exporter)
)

# Destination 3: Console (for debugging)
logger_provider.add_log_record_processor(
    BatchLogRecordProcessor(ConsoleLogRecordExporter())
)

# Use Python's standard logging, bridged to OpenTelemetry
logger = logging.getLogger("myapp")
logger.setLevel(logging.INFO)
logger.info("Logs are exported to all three destinations.")
logger.warning("This warning also goes everywhere.")

logger_provider.shutdown()
