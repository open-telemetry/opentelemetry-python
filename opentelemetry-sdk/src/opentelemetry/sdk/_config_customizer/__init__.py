from abc import ABC, abstractmethod
from opentelemetry.sdk._logs.export import LogExporter
from opentelemetry.sdk.metrics.export import (
    MetricExporter,
)
from typing import Type
from opentelemetry.sdk.trace.export import SpanExporter


# Class which can be used to customize the configurator.
class _BaseConfiguratorCustomizer(ABC):
    @abstractmethod
    def init_log_exporter(
        self, log_exporter: Type[LogExporter]
    ) -> LogExporter:
        pass

    @abstractmethod
    def init_metric_exporter(
        self,
        metric_exporter: Type[MetricExporter],
    ) -> MetricExporter:
        pass

    @abstractmethod
    def init_span_exporter(
        self,
        span_exporter: Type[SpanExporter],
    ) -> SpanExporter:
        pass

    @abstractmethod
    def init_resource(self):
        pass