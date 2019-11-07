import os
import requests

from opentelemetry import trace
from opentelemetry.ext import http_requests
from opentelemetry.ext.jaeger import JaegerSpanExporter
from opentelemetry.sdk.trace import Tracer
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

trace.set_preferred_tracer_implementation(lambda T: Tracer())
tracer = trace.tracer()

if os.getenv("EXPORTER") == "jaeger":
    exporter = JaegerSpanExporter(
        service_name="http-client",
        agent_host_name="localhost",
        agent_port=6831,
    )
else:
    exporter = ConsoleSpanExporter()

span_processor = BatchExportSpanProcessor(exporter)
tracer.add_span_processor(span_processor)

http_requests.enable(tracer)
response = requests.get(url="http://127.0.0.1:5000/")
span_processor.shutdown()
