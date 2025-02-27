from abc import ABC
from typing import Union

from opentelemetry.exporter.otlp.proto.http._log_exporter import (
    OTLPLogExporter,
)
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)

# TODO: import grpc exporters.

BaseOTLPExporters = Union[
    OTLPLogExporter, OTLPSpanExporter, OTLPMetricExporter
]


class OTLPExporterCustomizerBase(ABC):
    def customize_exporter(exporter: BaseOTLPExporters):
        pass
