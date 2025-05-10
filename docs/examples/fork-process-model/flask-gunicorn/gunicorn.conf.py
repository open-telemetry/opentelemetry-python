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

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

bind = "127.0.0.1:8000"

# Sample Worker processes
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Sample logging
errorlog = "-"
loglevel = "info"
accesslog = "-"
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
)


def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

    resource = Resource.create(
        attributes={
            SERVICE_NAME: "api-service",
            # If workers are not distinguished within attributes, traces and
            # metrics exported from each worker will be indistinguishable. While
            # not necessarily an issue for traces, it is confusing for almost
            # all metric types. A built-in way to identify a worker is by PID
            # but this may lead to high label cardinality. An alternative
            # workaround and additional discussion are available here:
            # https://github.com/benoitc/gunicorn/issues/1352
            "worker": worker.pid,
        }
    )

    trace.set_tracer_provider(TracerProvider(resource=resource))
    # This uses insecure connection for the purpose of example. Please see the
    # OTLP Exporter documentation for other options.
    span_processor = BatchSpanProcessor(
        OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
    )
    trace.get_tracer_provider().add_span_processor(span_processor)

    reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint="http://localhost:4317")
    )
    metrics.set_meter_provider(
        MeterProvider(
            resource=resource,
            metric_readers=[reader],
        )
    )
