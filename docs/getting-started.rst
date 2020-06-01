Getting Started with OpenTelemetry Python
=========================================

This guide will walk you through instrumenting a Python application with ``opentelemetry-python``.

For more elaborate examples, see `examples`.

Hello world: emitting a trace to your console
---------------------------------------------

To get started, install both the opentelemetry API and SDK:

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk

The API package provides the interfaces required by the application owner, as well
as some helper logic to load implementations.

The SDK provides an implementation of those interfaces, designed to be generic and extensible enough
that in many situations, the SDK will be sufficient.

Once installed, we can now utilize the packages to emit spans from your application. A span
represents an action within your application that you want to instrument, such as an HTTP request
or a database call. Once instrumented, the application owner can extract helpful information such as
how long the action took, or add arbitrary attributes to the span that may provide more insight for debugging.

Here's an example of a script that emits a trace containing three named spans: "foo", "bar", and "baz":

.. literalinclude:: getting_started/tracing_example.py
    :language: python
    :lines: 15-

We can run it, and see the traces print to your console:

.. code-block:: sh

    $ python tracing_example.py
    {
        "name": "baz",
        "context": {
            "trace_id": "0xb51058883c02f880111c959f3aa786a2",
            "span_id": "0xb2fa4c39f5f35e13",
            "trace_state": "{}"
        },
        "kind": "SpanKind.INTERNAL",
        "parent_id": "0x77e577e6a8813bf4",
        "start_time": "2020-05-07T14:39:52.906272Z",
        "end_time": "2020-05-07T14:39:52.906343Z",
        "status": {
            "canonical_code": "OK"
        },
        "attributes": {},
        "events": [],
        "links": []
    }
    {
        "name": "bar",
        "context": {
            "trace_id": "0xb51058883c02f880111c959f3aa786a2",
            "span_id": "0x77e577e6a8813bf4",
            "trace_state": "{}"
        },
        "kind": "SpanKind.INTERNAL",
        "parent_id": "0x3791d950cc5140c5",
        "start_time": "2020-05-07T14:39:52.906230Z",
        "end_time": "2020-05-07T14:39:52.906601Z",
        "status": {
            "canonical_code": "OK"
        },
        "attributes": {},
        "events": [],
        "links": []
    }
    {
        "name": "foo",
        "context": {
            "trace_id": "0xb51058883c02f880111c959f3aa786a2",
            "span_id": "0x3791d950cc5140c5",
            "trace_state": "{}"
        },
        "kind": "SpanKind.INTERNAL",
        "parent_id": null,
        "start_time": "2020-05-07T14:39:52.906157Z",
        "end_time": "2020-05-07T14:39:52.906743Z",
        "status": {
            "canonical_code": "OK"
        },
        "attributes": {},
        "events": [],
        "links": []
    }

Each span typically represents a single operation or unit of work.
Spans can be nested, and have a parent-child relationship with other spans.
While a given span is active, newly-created spans will inherit the active span's trace ID, options, and other attributes of its context.
A span without a parent is called the "root span", and a trace is comprised of one root span and its descendants.

In the example above, the OpenTelemetry Python library creates one trace containing three spans and prints it to STDOUT.

Configure exporters to emit spans elsewhere
-------------------------------------------

The example above does emit information about all spans, but the output is a bit hard to read.
In common cases, you would instead *export* this data to an application performance monitoring backend, to be visualized and queried.
It is also common to aggregate span and trace information from multiple services into a single database, so that actions that require multiple services can still all be visualized together.

This concept is known as distributed tracing. One such distributed tracing backend is known as Jaeger.

The Jaeger project provides an all-in-one docker container that provides a UI, database, and consumer. Let's bring
it up now:

.. code-block:: sh

    docker run -p 16686:16686 -p 6831:6831/udp jaegertracing/all-in-one

This will start Jaeger on port 16686 locally, and expose Jaeger thrift agent on port 6831. You can visit it at http://localhost:16686.

With this backend up, your application will now need to export traces to this system. ``opentelemetry-sdk`` does not provide an exporter
for Jaeger, but you can install that as a separate package:

.. code-block:: sh

    pip install opentelemetry-ext-jaeger

Once installed, update your code to import the Jaeger exporter, and use that instead:

.. literalinclude:: getting_started/jaeger_example.py
    :language: python
    :lines: 15-

Run the script:

.. code-block:: python

    python jaeger_example.py

You can then visit the jaeger UI, see you service under "services", and find your traces!

.. image:: images/jaeger_trace.png

Integrations example with Flask
-------------------------------

The above is a great example, but it's very manual. Within the telemetry space, there are common actions that one wants to instrument:

* HTTP responses from web services
* HTTP requests from clients
* Database calls

To help instrument common scenarios, opentelemetry also has the concept of "instrumentations": packages that are designed to interface
with a specific framework or library, such as Flask and psycopg2. A list of the currently curated extension packages can be found :scm_web:`here <ext/>`.

We will now instrument a basic Flask application that uses the requests library to send HTTP requests. First, install the instrumentation packages themselves:

.. code-block:: sh

    pip install opentelemetry-ext-flask
    pip install opentelemetry-ext-requests


And let's write a small Flask application that sends an HTTP request, activating each instrumentation during the initialization:

.. literalinclude:: getting_started/flask_example.py
    :language: python
    :lines: 15-


Now run the above script, hit the root url (http://localhost:5000/) a few times, and watch your spans be emitted!

.. code-block:: sh

   python flask_example.py


Adding Metrics
--------------

Spans are a great way to get detailed information about what your application is doing, but
what about a more aggregated perspective? OpenTelemetry provides supports for metrics, a time series
of numbers that might express things such as CPU utilization, request count for an HTTP server, or a
business metric such as transactions.

All metrics can be annotated with labels: additional qualifiers that help describe what
subdivision of the measurements the metric represents.

The following is an example of emitting metrics to console, in a similar fashion to the trace example:

.. literalinclude:: getting_started/metrics_example.py
    :language: python
    :lines: 15-

The sleeps will cause the script to take a while, but running it should yield:

.. code-block:: sh

    $ python metrics_example.py
    ConsoleMetricsExporter(data="Counter(name="requests", description="number of requests")", labels="(('environment', 'staging'),)", value=25)
    ConsoleMetricsExporter(data="Counter(name="requests", description="number of requests")", labels="(('environment', 'staging'),)", value=45)

Using Prometheus
----------------

Similar to traces, it is really valuable for metrics to have its own data store to help visualize and query the data. A common solution for this is
`Prometheus <https://prometheus.io/>`_.

Let's start by bringing up a Prometheus instance ourselves, to scrape our application. Write the following configuration:

.. code-block:: yaml

    # /tmp/prometheus.yml
    scrape_configs:
    - job_name: 'my-app'
      scrape_interval: 5s
      static_configs:
      - targets: ['localhost:8000']

And start a docker container for it:

.. code-block:: sh

    # --net=host will not work properly outside of Linux.
    docker run --net=host -v /tmp/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus \
        --log.level=debug --config.file=/etc/prometheus/prometheus.yml

For our Python application, we will need to install an exporter specific to Prometheus:

.. code-block:: sh

    pip install opentelemetry-ext-prometheus


And use that instead of the `ConsoleMetricsExporter`:

.. literalinclude:: getting_started/prometheus_example.py
    :language: python
    :lines: 15-

The Prometheus server will run locally on port 8000, and the instrumented code will make metrics available to Prometheus via the `PrometheusMetricsExporter`.
Visit the Prometheus UI (http://localhost:9090) to view your metrics.


Using the OpenTelemetry Collector for traces and metrics
--------------------------------------------------------

Although it's possible to directly export your telemetry data to specific backends, you may more complex use cases, including:

* having a single telemetry sink shared by multiple services, to reduce overhead of switching exporters
* aggregating metrics or traces across multiple services, running on multiple hosts

To enable a broad range of aggregation strategies, OpenTelemetry provides the `opentelemetry-collector <https://github.com/open-telemetry/opentelemetry-collector>`_.
The Collector is a flexible application that can consume trace and metric data and export to multiple other backends, including to another instance of the Collector.

To see how this works in practice, let's start the Collector locally. Write the following file:

.. code-block:: yaml

    # /tmp/otel-collector-config.yaml
    receivers:
        opencensus:
            endpoint: 0.0.0.0:55678
    exporters:
        logging:
            loglevel: debug
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

Start the docker container:

.. code-block:: sh

    docker run -p 55678:55678 \
        -v /tmp/otel-collector-config.yaml:/etc/otel-collector-config.yaml \
        omnition/opentelemetry-collector-contrib:latest \
        --config=/etc/otel-collector-config.yaml

Install the OpenTelemetry Collector exporter:

.. code-block:: sh

    pip install opentelemetry-ext-otcollector

And execute the following script:

.. literalinclude:: getting_started/otcollector_example.py
    :language: python
    :lines: 15-
