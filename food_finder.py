import json
import os
import time

from flask import Flask
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.ext.flask import FlaskInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleExportSpanProcessor,
)
from opentelemetry.tools.resource_detector import GoogleCloudResourceDetector
from opentelemetry.sdk.resources import get_aggregated_resources
import opentelemetry.ext.requests
import requests

app = Flask(__name__)
resources = get_aggregated_resources([GoogleCloudResourceDetector()])
trace.set_tracer_provider(TracerProvider(resource=resources))
opentelemetry.ext.requests.RequestsInstrumentor().instrument()

FlaskInstrumentor().instrument_app(app)


def slim_print(span):
    span_json = json.loads(span.to_json())
    return (
            json.dumps(
                {
                    "name": span_json["name"],
                    "context": span_json["context"],
                    "parent_id": span_json["parent_id"],
                }
            )
            + os.linesep
    )


cloud_exporter = CloudTraceSpanExporter(project_id='aaxue-gke')
console_export = ConsoleSpanExporter(formatter=slim_print)

trace.get_tracer_provider().add_span_processor(
    SimpleExportSpanProcessor(cloud_exporter)
)

port = 5010
talk_to = None

_GCP_METADATA_URL = (
    "http://metadata.google.internal/computeMetadata/v1/?recursive=true"
)
_GCP_METADATA_URL_HEADER = {"Metadata-Flavor": "Google"}
@app.route("/opentelemetry_server_flask_" + str(port), methods=["GET"])
def opentelemetry_server_flask():
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(
            "opentelemetry_server_manual_" + str(port)):
        time.sleep(0.5)
        if talk_to:
            requests.get(talk_to)

        return 'existing {}\n\n\n metadta {}'.format(resources.labels, requests.get(
            _GCP_METADATA_URL, headers=_GCP_METADATA_URL_HEADER
        ).json())


if __name__ == "__main__":
    port = os.getenv('PORT') or port
    print("running finder")
    app.run(host='0.0.0.0', port=port)