# Copyright 2019, OpenTelemetry Authors
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

import logging
import typing
from enum import Enum

from .. import Span, SpanProcessor

logger = logging.getLogger(__name__)


class SpanExportResult(Enum):
    SUCCESS = 0
    FAILED_RETRYABLE = 1
    FAILED_NOT_RETRYABLE = 2


class SpanExporter:
    """Interface for exporting spans.

    Interface to be implemented by services that want to export recorded in
    its own format.

    To export data this MUST be registered to the :class`..Tracer` using a
    `SimpleExportSpanProcessor` or a `BatchSpanProcessor`.
    """

    def export(self, spans: typing.Sequence[Span]) -> "SpanExportResult":
        """Exports a batch of telemetry data.

        Args:
            spans: The list of `Span`s to be exported

        Returns:
            The result of the export
        """

    def shutdown(self) -> None:
        """Shuts down the exporter.

        Called when the SDK is shut down.
        """


class SimpleExportSpanProcessor(SpanProcessor):
    """Simple SpanProcessor implementation.

    SimpleExportSpanProcessor is an implementation of `SpanProcessor` that
    passes ended spans directly to the configured `SpanExporter`.
    """

    def __init__(self, span_exporter: SpanExporter):
        self.span_exporter = span_exporter

    def on_start(self, span: Span) -> None:
        pass

    def on_end(self, span: Span) -> None:
        try:
            self.span_exporter.export((span,))
        # pylint: disable=broad-except
        except Exception as exc:
            logger.warning("Exception while exporting data: %s", exc)

    def shutdown(self) -> None:
        self.span_exporter.shutdown()


class ConsoleSpanExporter(SpanExporter):
    """Implementation of :class:`SpanExporter` that prints spans to the
    console.

    This class can be used for diagnostic purposes. It prints the exported
    spans to the console STDOUT.
    """

    def export(self, spans: typing.Sequence[Span]) -> SpanExportResult:
        for span in spans:
            print(span)
        return SpanExportResult.SUCCESS
