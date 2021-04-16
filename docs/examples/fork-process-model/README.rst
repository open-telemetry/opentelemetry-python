Working With Fork Process Models
================================

The `BatchSpanProcessor` is not fork-safe and doesn't work well with application servers
(Gunicorn, uWSGI) which are based on the pre-fork web server model. The `BatchSpanProcessor`
spawns a thread to run in the background to export spans to the telemetry backend. During the fork, the child
process inherits the lock which is held by the parent process and deadlock occurs. We can use fork hooks to
get around this limitation of the span processor.

Please see http://bugs.python.org/issue6721 for the problems about Python locks in (multi)threaded
context with fork.

Gunicorn post_fork hook
-----------------------

.. code-block:: python

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
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


uWSGI postfork decorator
------------------------

.. code-block:: python

    from uwsgidecorators import postfork

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor


    @postfork
    def init_tracing():
        resource = Resource.create(attributes={
            "service.name": "api-service"
        })

        trace.set_tracer_provider(TracerProvider(resource=resource))
        span_processor = BatchSpanProcessor(
            OTLPSpanExporter(endpoint="http://localhost:4317")
        )
        trace.get_tracer_provider().add_span_processor(span_processor)


The source code for the examples with Flask app are available :scm_web:`here <docs/examples/fork-process-model/>`.
