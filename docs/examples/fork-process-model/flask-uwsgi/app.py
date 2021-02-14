import flask
from flask import request
from uwsgidecorators import postfork

from opentelemetry import trace
from opentelemetry.exporter.jaeger import JaegerSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

trace.set_tracer_provider(TracerProvider())

application = flask.Flask(__name__)

FlaskInstrumentor().instrument_app(application)
tracer = trace.get_tracer(__name__)


@postfork
def set_span_processor():
    trace.get_tracer_provider().add_span_processor(
        BatchExportSpanProcessor(JaegerSpanExporter(service_name="my-service"))
    )


def fib_slow(n):
    if n <= 1:
        return n
    return fib_slow(n - 1) + fib_fast(n - 2)


def fib_fast(n):
    nth_fib = [0] * (n + 2)
    nth_fib[1] = 1
    for i in range(2, n + 1):
        nth_fib[i] = nth_fib[i - 1] + nth_fib[i - 2]
    return nth_fib[n]


@application.route("/fibonacci")
def fibonacci():
    n = int(request.args.get("n", 1))
    with tracer.start_as_current_span("root"):
        with tracer.start_as_current_span("fib_slow") as slow_span:
            ans = fib_slow(n)
            slow_span.set_attribute("n", n)
            slow_span.set_attribute("nth_fibonacci", ans)
        with tracer.start_as_current_span("fib_fast") as fast_span:
            ans = fib_fast(n)
            fast_span.set_attribute("n", n)
            fast_span.set_attribute("nth_fibonacci", ans)

    return "Hello"


if __name__ == "__main__":
    application.run()
