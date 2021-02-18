Working With Fork Process Models
================================

The `BatchExportSpanProcessor` is not fork-safe and doesn't work well with application servers
(Gunicorn, uWSGI) which are based on the pre-fork web server model. The `BatchExportSpanProcessor`
spawns a thread to run in the background to export spans to the telemetry backend. During the fork, the child
process inherits the lock which is held by the parent process and deadlock occurs. We can use fork hooks to
get around this limitation of the span processor.

Please see http://bugs.python.org/issue6721 for the problems about Python locks in (multi)threaded
context with fork.

Gunicorn post_fork hook
-----------------------

.. code-block:: python

    from opentelemetry import trace
    from opentelemetry.exporter.jaeger import JaegerSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchExportSpanProcessor


    def post_fork(server, worker):
        server.log.info("Worker spawned (pid: %s)", worker.pid)
        trace.set_tracer_provider(TracerProvider())
        trace.get_tracer_provider().add_span_processor(
            BatchExportSpanProcessor(JaegerSpanExporter(service_name='my-service'))
        )


uWSGI postfork decorator
------------------------

.. code-block:: python

    from opentelemetry import trace
    from opentelemetry.exporter.jaeger import JaegerSpanExporter
    from opentelemetry.sdk.trace.export import BatchExportSpanProcessor


    @postfork
    def set_span_processor():
        trace.get_tracer_provider().add_span_processor(
            BatchExportSpanProcessor(JaegerSpanExporter(service_name='my-service'))
        )


The source code for the examples with Flask app are available :scm_web:`here <docs/examples/fork-process-model/>`.
