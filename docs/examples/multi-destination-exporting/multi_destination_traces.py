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
This example shows how to export traces to multiple destinations.
Each BatchSpanProcessor has its own queue and retry logic, so
destinations do not block each other.
"""

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as GrpcSpanExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as HttpSpanExporter,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)

provider = TracerProvider()
trace.set_tracer_provider(provider)

# Destination 1: OTLP over gRPC
grpc_exporter = GrpcSpanExporter(
    endpoint="http://localhost:4317", insecure=True
)
provider.add_span_processor(BatchSpanProcessor(grpc_exporter))

# Destination 2: OTLP over HTTP
http_exporter = HttpSpanExporter(endpoint="http://localhost:4318/v1/traces")
provider.add_span_processor(BatchSpanProcessor(http_exporter))

# Destination 3: Console (for debugging)
provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("example-request"):
    with tracer.start_as_current_span("fetch-data"):
        print("Spans are exported to all three destinations.")

provider.shutdown()
