# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from mysql.connector import connect

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.instrumentation.mysql import MySQLInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

resource = Resource.create(
    attributes={
        "service.name": "sqlcommenter-example",
    }
)
trace.set_tracer_provider(TracerProvider(resource=resource))
span_processor = BatchSpanProcessor(
    OTLPSpanExporter(endpoint="http://localhost:4317")
)
trace.get_tracer_provider().add_span_processor(span_processor)

cnx = connect(
    host="localhost",
    port=3366,
    user="books",
    password="books123",
    database="books",
)

# Instruments MySQL queries with sqlcommenter enabled
# and comment-in-span-attribute enabled.
# Returns wrapped connection to generate traces.
cnx = MySQLInstrumentor().instrument_connection(
    connection=cnx,
    enable_commenter=True,
    enable_attribute_commenter=True,
)

cursor = cnx.cursor()
statement = "SELECT * FROM authors WHERE id = %s"

# Each SELECT query generates one mysql log with sqlcomment
# and one OTel span with `db.statement` attribute that also
# includes sqlcomment.
for cid in range(1, 4):
    cursor.execute(statement, (cid,))
    rows = cursor.fetchall()
    print(f"Found author: {rows[0]}")

print("Done.")
