Working With Fork Process Models
================================

The tracing and logging batch processors reinitialize their background worker
state after a process forks, so they can be created before application servers
such as Gunicorn and uWSGI fork their workers. Metrics aggregation state is not
safe to share across forked workers, however. Applications using metrics with a
pre-fork server should create their ``MeterProvider`` and metric readers in each
child process.

The examples below initialize tracing and metrics together in a fork hook. Only
the metrics setup requires this placement, but keeping the providers together
gives every worker a consistent resource and avoids sharing metric state. An
application that emits only traces or logs can initialize its providers before
the server forks.

Please see https://bugs.python.org/issue6721 for general problems involving
Python locks in multithreaded programs that fork.

The source code for the examples with Flask app are available :scm_web:`here <docs/examples/fork-process-model/>`.

Gunicorn post_fork hook
-----------------------

.. code-block:: python

    from opentelemetry import metrics, trace
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor


    def post_fork(server, worker):
        server.log.info("Worker spawned (pid: %s)", worker.pid)

        resource = Resource.create(attributes={
            "service.name": "api-service"
        })

        trace.set_tracer_provider(TracerProvider(resource=resource))
        span_processor = BatchSpanProcessor(
            OTLPSpanExporter(endpoint="http://localhost:4317")
        )
        trace.get_tracer_provider().add_span_processor(span_processor)

        metrics.set_meter_provider(
            MeterProvider(
                resource=resource,
                metric_readers=[
                    PeriodicExportingMetricReader(
                        OTLPMetricExporter(endpoint="http://localhost:4317")
                    )
                ],
            )
        )


uWSGI postfork decorator
------------------------

.. code-block:: python

    from uwsgidecorators import postfork

    from opentelemetry import metrics, trace
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor


    @postfork
    def init_telemetry():
        resource = Resource.create(attributes={
            "service.name": "api-service"
        })

        trace.set_tracer_provider(TracerProvider(resource=resource))
        span_processor = BatchSpanProcessor(
            OTLPSpanExporter(endpoint="http://localhost:4317")
        )
        trace.get_tracer_provider().add_span_processor(span_processor)

        metrics.set_meter_provider(
            MeterProvider(
                resource=resource,
                metric_readers=[
                    PeriodicExportingMetricReader(
                        OTLPMetricExporter(endpoint="http://localhost:4317")
                    )
                ],
            )
        )
