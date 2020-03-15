Getting Started with OpenTelemetry Python
=========================================

This guide will walk you through instrumenting a python application with opentelemetry-python.

Hello world: emitting a trace to your console
---------------------------------------------

To get started, install both the opentelemetry api and sdk:

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk

The api package provides the interfaces required by the application owner, as well
as some helper logic to load implementations.

The sdk provides an implementation of those interfaces, designed to be generic and extensible enough
that in many situations, the sdk will be sufficient.

Once installed, we can now utilize the packages to emit spans from your application. A span 
represents an action within your application that you want to instrument, such as an http request
or a database call. Once instrumented, the application owner can extract helpful information such as
how long the action took, or add arbitrary attributes to the span that may provide more insight for debugging.

Here's an example of a script that emits traces three actions, foo, bar, and baz:

.. code-block:: python

    # example.py
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter
    from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor

    trace.set_tracer(TracerProvider())
    trace.get_tracer_provider().add_span_processor(
        SimpleExportSpanProcessor(ConsoleSpanExporter())
    )
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span('foo'):
        with tracer.start_as_current_span('bar'):
            with tracer.start_as_current_span('baz'):
                print("Hello world from OpenTelemetry Python!")

We can run it, and see the traces print to your console:

.. code-block:: sh

    $ python /tmp/example.py
    Hello world from OpenTelemetry Python!
    Span(name="baz", context=SpanContext(trace_id=0x37c1b154d9ab5a4b94b0046484b90400, span_id=0xfacbb82a4d0cf5dd, trace_state={}), kind=SpanKind.INTERNAL, parent=Span(name="bar", context=SpanContext(trace_id=0x37c1b154d9ab5a4b94b0046484b90400, span_id=0xb1894e8d588f5f62, trace_state={})), start_time=2020-03-15T05:12:08.345394Z, end_time=2020-03-15T05:12:08.345450Z)
    Span(name="bar", context=SpanContext(trace_id=0x37c1b154d9ab5a4b94b0046484b90400, span_id=0xb1894e8d588f5f62, trace_state={}), kind=SpanKind.INTERNAL, parent=Span(name="foo", context=SpanContext(trace_id=0x37c1b154d9ab5a4b94b0046484b90400, span_id=0xde5ea23d6a9e4180, trace_state={})), start_time=2020-03-15T05:12:08.345360Z, end_time=2020-03-15T05:12:08.345597Z)
    Span(name="foo", context=SpanContext(trace_id=0x37c1b154d9ab5a4b94b0046484b90400, span_id=0xde5ea23d6a9e4180, trace_state={}), kind=SpanKind.INTERNAL, parent=None, start_time=2020-03-15T05:12:08.345287Z, end_time=2020-03-15T05:12:08.345673Z)


Spans can be nested into each other. The top-level span is known by a special name, as the "trace".
the top-level span creates a trace id, which is inherited by all child spans.

Configure exporters to emit spans elsewhere
-------------------------------------------

The example above does emit information about all spans, but the output is a bit hard to read.
In common cases, you would instead *export* this data to some consuming service, to be visualized and
easily queryable. It is also common to aggregate span and trace information from multiple services into
a single database, so that actions that require multiple services can still all be visualized together.

This concept is known as distributed tracing. One such distributed tracing backend is known as jaeger.

The jaeger project provides an all-in-one docker container that provides a UI, database, and consumer. Let's bring
it up now:

.. code-block:: sh

    docker run -p 16686:16686 jaegertracing/all-in-one

This will start jaeger on port 16686 locally. You can visit it at http://localhost:16686:

With this backend up, your application will now need to export traces to this system. The opentelemetry-sdk does not provide an exporter
for jaeger, but you can install that as a separate package:

.. code-block:: sh

    pip install opentelemetry-ext-jaeger

Once installed, update your code to import the jaeger exporter, and use that instead:

.. code-block:: python

    # example.py
    from opentelemetry import trace
    from opentelemetry.ext import jaeger
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor

    trace.set_tracer_provider(TracerProvider())

    # create a JaegerSpanExporter
    jaeger_exporter = jaeger.JaegerSpanExporter(
        service_name='my-helloworld-service',
        collector_host_name='localhost',
        collector_port=14268,
        collector_endpoint='/api/traces?format=jaeger.thrift',
    )

    trace.get_tracer_provider().add_span_processor(
        SimpleExportSpanProcessor(jaeger_exporter)
    )
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span('foo'):
        with tracer.start_as_current_span('bar'):
            with tracer.start_as_current_span('baz'):
                print("Hello world from OpenTelemetry Python!")

Integrations example with flask
-------------------------------

.. code-block:: sh

    pip install opentelemetry-ext-flask
    pip install opentelemetry-ext-http-requests


.. code-block:: python

    import flask
    import requests

    import opentelemetry.ext.http_requests
    from opentelemetry import trace
    from opentelemetry.ext.flask import instrument_app
    from opentelemetry.sdk.trace import TracerProvider


    app = flask.Flask(__name__)
    trace.set_tracer_provider(TracerProvider())
    opentelemetry.ext.http_requests.enable(trace.get_tracer_provider())
    instrument_app(app)


    @app.route("/")
    def hello():
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("example-request"):
            requests.get("http://www.example.com")
        return "hello"


Adding Metrics
--------------

.. code-block:: python

    import sys
    import time

    from opentelemetry import metrics
    from opentelemetry.sdk.metrics import Counter, MeterProvider
    from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter
    from opentelemetry.sdk.metrics.export.controller import PushController

    batcher_mode = "stateful"
    metrics.set_meter_provider(MeterProvider())
    meter = metrics.get_meter(__name__, batcher_mode == "stateful")
    exporter = ConsoleMetricsExporter()
    controller = PushController(meter, exporter, 5)

    staging_label_set = meter.get_label_set({"environment": "staging"})

    requests_counter = meter.create_metric(
        name="requests",
        description="number of requests",
        unit="1",
        value_type=int,
        metric_type=Counter,
        label_keys=("environment",),
    )

    requests_counter.add(25, staging_label_set)
    time.sleep(5)

    requests_counter.add(20, staging_label_set)
    time.sleep(5)


Using Prometheus
----------------

.. code-block:: yaml

    # configuration for prometheus
    scrape_configs:
    - job_name: 'my-app'
        scrape_interval: 5s
        static_configs:
        - targets: ['localhost:8000']

.. code-block:: sh

    docker run -p 9090:9090 -v /tmp/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus

.. code-block:: sh

    pip install opentelemetry-ext-prometheus

.. code-block:: python

    import sys
    import time

    from opentelemetry import metrics
    from opentelemetry.sdk.metrics import Counter, MeterProvider
    from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter
    from opentelemetry.sdk.metrics.export.controller import PushController
    from prometheus_client import start_http_server

    # Start Prometheus client
    start_http_server(port=8000, addr="localhost")

    batcher_mode = "stateful"
    metrics.set_meter_provider(MeterProvider())
    meter = metrics.get_meter(__name__, batcher_mode == "stateful")
    exporter = PrometheusMetricsExporter("MyAppPrefix")
    controller = PushController(meter, exporter, 5)

    staging_label_set = meter.get_label_set({"environment": "staging"})

    requests_counter = meter.create_metric(
        name="requests",
        description="number of requests",
        unit="1",
        value_type=int,
        metric_type=Counter,
        label_keys=("environment",),
    )

    requests_counter.add(25, staging_label_set)
    time.sleep(5)

    requests_counter.add(20, staging_label_set)
    time.sleep(5)

    # this line is added to keep the http server up long 
    # enough to scrape.
    input("Press any key to exit...")


Using the opentelemetry-collector for traces and metrics
========================================================


.. code-block:: yaml

    # /tmp/otel-collector-config.yaml
    receivers:
        opencensus:
            endpoint: 0.0.0.0:55678
    exporters:
        logging:
    processors:
        batch:
        queued_retry:
    service:
        pipelines:
            traces:
                receivers: [opencensus]
                exporters: [logging]
                processors: [batch, queued_retry]
            metrics:
                receivers: [opencensus]
                exporters: [logging]

.. code-block:: sh
 
    docker run -p 55678:55678\
        -v /tmp/otel-collector-config.yaml:/etc/otel-collector-config.yaml\
        omnition/opentelemetry-collector-contrib:latest \
        --config=/etc/otel-collector-config.yaml

.. code-block:: sh

    pip install opentelemetry-ext-otcollector

.. code-block:: python

    from opentelemetry import trace
    from opentelemetry.ext.otcollector.trace_exporter  import CollectorSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchExportSpanProcessor
    from opentelemetry import metrics
    from opentelemetry.ext.otcollector.metrics_exporter import CollectorMetricsExporter
    from opentelemetry.sdk.metrics import Counter, MeterProvider
    from opentelemetry.sdk.metrics.export.controller import PushController


    # create a CollectorSpanExporter
    collector_exporter = CollectorSpanExporter(
        # optional:
        # endpoint="myCollectorUrl:55678",
        # service_name="test_service",
        # host_name="machine/container name",
    )

    # create a CollectorMetricsExporter
    collector_exporter = CollectorMetricsExporter(
        # optional:
        # endpoint="myCollectorUrl:55678",
        # service_name="test_service",
        # host_name="machine/container name",
    )

    # Meter is responsible for creating and recording metrics
    metrics.set_preferred_meter_provider_implementation(lambda _: MeterProvider())
    meter = metrics.get_meter(__name__)
    # controller collects metrics created from meter and exports it via the
    # exporter every interval
    controller = PushController(meter, collector_exporter, 5)

    # Create a BatchExportSpanProcessor and add the exporter to it
    span_processor = BatchExportSpanProcessor(collector_exporter)

    # Configure the tracer to use the collector exporter
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(span_processor)
    tracer = TracerProvider().get_tracer(__name__)

    with tracer.start_as_current_span("foo"):
        print("Hello world!")

    counter = meter.create_metric(
        "requests",
        "number of requests",
        "requests",
        int,
        Counter,
        ("environment",),
    )
    # Labelsets are used to identify key-values that are associated with a specific
    # metric that you want to record. These are useful for pre-aggregation and can
    # be used to store custom dimensions pertaining to a metric
    label_set = meter.get_label_set({"environment": "staging"})
    
    counter.add(25, label_set)