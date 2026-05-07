# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from flask import Flask, request

from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.trace import get_tracer_provider, set_tracer_provider

set_tracer_provider(TracerProvider())
get_tracer_provider().add_span_processor(
    BatchSpanProcessor(ConsoleSpanExporter())
)

instrumentor = FlaskInstrumentor()

app = Flask(__name__)

instrumentor.instrument_app(app)
# instrumentor.instrument_app(app, excluded_urls="/server_request")


@app.route("/server_request")
def server_request():
    print(request.args.get("param"))
    return "served"


if __name__ == "__main__":
    app.run(port=8082)
