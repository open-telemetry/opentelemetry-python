import logging
from collections.abc import Callable, Sequence
from typing import IO

from opentelemetry.exporter.otlp.json.common.trace_encoder import encode_spans
from opentelemetry.exporter.otlp.json.file._internal import _format_line
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

_logger = logging.getLogger(__name__)


class FileSpanExporter(SpanExporter):
    def __init__(
        self,
        stream: IO[str],
        *,
        _formatter: Callable[[dict], str] | None = None,
    ) -> None:
        self._stream = stream
        self._formatter = _formatter or _format_line
        self._shutdown = False

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return SpanExportResult.FAILURE
        try:
            lines = [
                self._formatter(span.to_dict())
                for span in encode_spans(spans).resource_spans
            ]
            self._stream.writelines(lines)
            self._stream.flush()
            return SpanExportResult.SUCCESS
        except Exception as error:
            _logger.error("Failed to export span batch: %s", error)
        return SpanExportResult.FAILURE

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing."""
        return True
