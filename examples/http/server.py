import os

import flask
import requests
from opentelemetry import trace
from opentelemetry.ext import http_requests
from opentelemetry.ext.jaeger import JaegerSpanExporter
from opentelemetry.ext.wsgi import OpenTelemetryMiddleware
from opentelemetry.sdk.trace import Tracer
from opentelemetry.sdk.trace.export import (
    BatchExportSpanProcessor,
    ConsoleSpanExporter,
)

trace.set_preferred_tracer_implementation(lambda T: Tracer())
tracer = trace.tracer()

if os.getenv("EXPORTER") == "jaeger":
    exporter = JaegerSpanExporter(
        service_name="http-server",
        agent_host_name="localhost",
        agent_port=6831,
    )
else:
    exporter = ConsoleSpanExporter()

span_processor = BatchExportSpanProcessor(exporter)
tracer.add_span_processor(span_processor)

http_requests.enable(tracer)
app = flask.Flask(__name__)
app.wsgi_app = OpenTelemetryMiddleware(app.wsgi_app)


@app.route("/")
def hello():
    with tracer.start_as_current_span("parent"):
        requests.get("https://www.wikipedia.org/wiki/Rabbit")
    return "hello"


if __name__ == "__main__":
    app.run(debug=True)
    span_processor.shutdown()
