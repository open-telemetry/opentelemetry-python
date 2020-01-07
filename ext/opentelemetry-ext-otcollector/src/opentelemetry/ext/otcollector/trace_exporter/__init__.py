# Copyright 2020, OpenTelemetry Authors
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

"""OpenTelemetry Collector Exporter."""

import grpc
import logging
from typing import Optional, Sequence

from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import Span, SpanContext, SpanKind

DEFAULT_SERVICE_NAME = "collector-exporter"
DEFAULT_ENDPOINT = "http://localhost:55678/v1/trace"

logger = logging.getLogger(__name__)


class CollectorSpanExporter(SpanExporter):
    """OpenTelemetry Collector span exporter.

    Args:
        service_name: Name of Collector service.
        endpoint: OpenTelemetry Collector endpoint.
    """

    def __init__(
        self,
        service_name: str =DEFAULT_SERVICE_NAME,
        endpoint: str = DEFAULT_ENDPOINT,
    ):
        self.service_name = service_name
        self.endpoint = endpoint

    def export(self, spans: Sequence[Span]) -> SpanExportResult:
        collector_spans = self._translate_to_collector(spans)
        
        try:
            
        except grpc.RpcError:
            return SpanExportResult.FAILED_NOT_RETRYABLE

        return SpanExportResult.SUCCESS

    def _translate_to_collector(self, spans: Sequence[Span]):
        collector_spans = []
        for span in spans:
            collector_span = {}
            collector_spans.append(collector_span)
        return collector_spans

    def shutdown(self) -> None:
        pass