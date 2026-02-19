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

import sqlite3

from flask import Flask
from opencensus.ext.flask.flask_middleware import FlaskMiddleware

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.shim.opencensus import install_shim

DB = "example.db"

# Set up OpenTelemetry
tracer_provider = TracerProvider(
    resource=Resource.create(
        {
            "service.name": "opencensus-shim-example-flask",
        }
    )
)
trace.set_tracer_provider(tracer_provider)

# Configure OTel to export traces to Jaeger
tracer_provider.add_span_processor(
    BatchSpanProcessor(
        OTLPSpanExporter(
            endpoint="localhost:4317",
        )
    )
)
tracer = tracer_provider.get_tracer(__name__)

# Install the shim to start bridging spans from OpenCensus to OpenTelemetry
install_shim()

# Instrument sqlite3 library
SQLite3Instrumentor().instrument()

# Setup Flask with OpenCensus instrumentation
app = Flask(__name__)
FlaskMiddleware(app)


# Setup the application database
def setup_db():
    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS movie(
                title,
                year,
                PRIMARY KEY(title, year)
            )
            """
        )
        cur.execute(
            """
            INSERT OR IGNORE INTO movie(title, year) VALUES
                ('Mission Telemetry', 2000),
                ('Observing the World', 2010),
                ('The Tracer', 1999),
                ('The Instrument', 2020)
            """
        )


setup_db()


@app.route("/")
def hello_world():
    lines = []
    with tracer.start_as_current_span("query movies from db"), sqlite3.connect(
        DB
    ) as con:
        cur = con.cursor()
        for title, year in cur.execute("SELECT title, year from movie"):
            lines.append(f"<li>{title} is from the year {year}</li>")

    with tracer.start_as_current_span("build response html"):
        html = f"<ul>{''.join(lines)}</ul>"

    return html
