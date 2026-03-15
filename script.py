import logging
import time

from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.sdk.trace.export._async import (
    AsyncBatchSpanProcessor,
)
from opentelemetry.sdk.trace import TracerProvider

logging.basicConfig(level=logging.DEBUG)

tp = TracerProvider()
tp.add_span_processor(
    AsyncBatchSpanProcessor(
        ConsoleSpanExporter(out=open("./spans.log", "w+")),
        schedule_delay_millis=1000,
    )
)
t = tp.get_tracer(__name__)


def main() -> None:
    # write spans and allow them to export
    for _ in range(10):
        with t.start_as_current_span("foo"):
            pass

    time.sleep(2.5)

    # write spans and force flush them immediately
    for _ in range(10):
        with t.start_as_current_span("flushme"):
            pass

    tp.force_flush()
    time.sleep(2.5)

    # write spans and allow shutdown to flush them
    for _ in range(10):
        with t.start_as_current_span("shutmedown"):
            pass


main()

tp.shutdown()
