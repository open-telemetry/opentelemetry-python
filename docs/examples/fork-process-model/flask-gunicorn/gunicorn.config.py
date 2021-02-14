from opentelemetry import trace
from opentelemetry.exporter.jaeger import JaegerSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor


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
    trace.set_tracer_provider(TracerProvider())
    trace.get_tracer_provider().add_span_processor(
        BatchExportSpanProcessor(JaegerSpanExporter(service_name="my-service"))
    )
