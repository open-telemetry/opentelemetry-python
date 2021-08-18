import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.log_exporter import OTLPLogExporter
from opentelemetry.sdk.logs import OTLPHandler, get_log_emitter_provider
from opentelemetry.sdk.logs.export import SimpleLogProcessor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    SimpleSpanProcessor(ConsoleSpanExporter())
)

log_emitter_provider = get_log_emitter_provider()
exporter = OTLPLogExporter(insecure=True)
log_emitter_provider.add_log_processor(SimpleLogProcessor(exporter))
log_emitter = log_emitter_provider.get_log_emitter(__name__, "0.1")
handler = OTLPHandler(level=logging.NOTSET, log_emitter=log_emitter)

# Attach OTLP handler to root logger
logging.getLogger("root").addHandler(handler)

# Log directly
logging.info("Jackdaws love my big sphinx of quartz.")

# Create different namespaced loggers
logger1 = logging.getLogger("myapp.area1")
logger2 = logging.getLogger("myapp.area2")

logger1.debug("Quick zephyrs blow, vexing daft Jim.")
logger1.info("How quickly daft jumping zebras vex.")
logger2.warning("Jail zesty vixen who grabbed pay from quack.")
logger2.error("The five boxing wizards jump quickly.")


# Trace context correlation
tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("foo"):
    # Do something
    logger2.error("Hyderabad, we have a major problem.")

log_emitter_provider.shutdown()
