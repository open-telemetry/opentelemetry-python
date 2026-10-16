Working With Fork Process Models
================================

The `BatchSpanProcessor` uses a background thread to export spans. Forking a
multithreaded process can leave a child with locks held by threads that no longer
exist. The current SDK reinitializes the processor's internal lock, event and
worker thread in the child and clears the inherited span queue. On platforms
that support ``os.register_at_fork``, this happens in an after-fork hook.

This support covers the processor's internal state, not every exporter or its
transport. An exporter may have its own restrictions on sharing connections
across a fork. Initializing the tracer provider, processor and exporter in each
worker avoids inheriting those connections and is a useful approach for manual
instrumentation with pre-fork servers such as Gunicorn and uWSGI.

The hooks below show how to initialize tracing in each worker. They are an
alternative to configuring tracing in the parent process, rather than a second
initialization step for applications that already configure tracing through
auto-instrumentation.

For signal-specific auto-instrumentation support and workarounds, see the
`Python auto-instrumentation troubleshooting guide
<https://opentelemetry.io/docs/zero-code/python/troubleshooting/#pre-fork-server-issues>`_.

Please see http://bugs.python.org/issue6721 for the problems about Python locks in (multi)threaded
context with fork.

The source code for the examples with Flask app are available :scm_web:`here <docs/examples/fork-process-model/>`.

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
