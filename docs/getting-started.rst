Getting Started with OpenTelemetry Python
=========================================

This guide walks you through instrumenting a Python application with ``opentelemetry-python``.

For more elaborate examples, see `examples <https://github.com/open-telemetry/opentelemetry-python/tree/main/docs/examples/>`_. 

Hello world: emit a trace to your console
---------------------------------------------

To get started, install both the opentelemetry API and SDK:

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk

The API package provides the interfaces required by the application owner, as well
as some helper logic to load implementations.

The SDK provides an implementation of those interfaces. The implementation is designed to be generic and extensible enough
that in many situations, the SDK is sufficient.

Once installed, you can use the packages to emit spans from your application. A span
represents an action within your application that you want to instrument, such as an HTTP request
or a database call. Once instrumented, you can extract helpful information such as
how long the action took. You can also add arbitrary attributes to the span that provide more insight for debugging.

The following example script emits a trace containing three named spans: "foo", "bar", and "baz":

.. literalinclude:: getting_started/tracing_example.py
    :language: python
    :lines: 15-

When you run the script you can see the traces printed to your console:

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
            "status_code": "OK"
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
            "status_code": "OK"
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
            "status_code": "OK"
        },
        "attributes": {},
        "events": [],
        "links": []
    }

Each span typically represents a single operation or unit of work.
Spans can be nested, and have a parent-child relationship with other spans.
While a given span is active, newly-created spans inherit the active span's trace ID, options, and other attributes of its context.
A span without a parent is called the root span, and a trace is comprised of one root span and its descendants.

In this example, the OpenTelemetry Python library creates one trace containing three spans and prints it to STDOUT.

Configure exporters to emit spans elsewhere
-------------------------------------------

The previous example does emit information about all spans, but the output is a bit hard to read.
In most cases, you can instead *export* this data to an application performance monitoring backend to be visualized and queried.
It's also common to aggregate span and trace information from multiple services into a single database, so that actions requiring multiple services can still all be visualized together.

This concept of aggregating span and trace information is known as distributed tracing. One such distributed tracing backend is known as Jaeger. The Jaeger project provides an all-in-one Docker container with a UI, database, and consumer. 

Run the following command to start Jaeger:

.. code-block:: sh

    docker run -p 16686:16686 -p 6831:6831/udp jaegertracing/all-in-one

This command starts Jaeger locally on port 16686 and exposes the Jaeger thrift agent on port 6831. You can visit Jaeger at http://localhost:16686.

After you spin up the backend, your application needs to export traces to this system. Although ``opentelemetry-sdk`` doesn't provide an exporter
for Jaeger, you can install it as a separate package with the following command:

.. code-block:: sh

    pip install opentelemetry-exporter-jaeger

After you install the exporter, update your code to import the Jaeger exporter and use that instead:

.. literalinclude:: getting_started/jaeger_example.py
    :language: python
    :lines: 15-

Finally, run the Python script:

.. code-block:: python

    python jaeger_example.py

You can then visit the Jaeger UI, see your service under "services", and find your traces!

.. image:: images/jaeger_trace.png

Instrumentation example with Flask
------------------------------------

While the example in the previous section is great, it's very manual. The following are common actions you might want to track and include as part of your distributed tracing.

* HTTP responses from web services
* HTTP requests from clients
* Database calls

To track these common actions, OpenTelemetry has the concept of instrumentations. Instrumentations are packages designed to interface
with a specific framework or library, such as Flask and psycopg2. You can find a list of the currently curated extension packages in the `Contrib repository <https://github.com/open-telemetry/opentelemetry-python-contrib/tree/main/instrumentation>`_.

Instrument a basic Flask application that uses the requests library to send HTTP requests. First, install the instrumentation packages themselves:

.. code-block:: sh

    pip install opentelemetry-instrumentation-flask
    pip install opentelemetry-instrumentation-requests


The following small Flask application sends an HTTP request and also activates each instrumentation during its initialization:

.. literalinclude:: getting_started/flask_example.py
    :language: python
    :lines: 15-


Now run the script, hit the root URL (http://localhost:5000/) a few times, and watch your spans be emitted!

.. code-block:: sh

   python flask_example.py


Configure Your HTTP propagator (b3, Baggage)
-------------------------------------------------------

A major feature of distributed tracing is the ability to correlate a trace across
multiple services. However, those services need to propagate information about a
trace from one service to the other.

To enable this propagation, OpenTelemetry has the concept of `propagators <https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/context/api-propagators.md>`_,
which provide a common method to encode and decode span information from a request and response, respectively.

By default, ``opentelemetry-python`` is configured to use the `W3C Trace Context <https://www.w3.org/TR/trace-context/>`_
and `W3C Baggage <https://www.w3.org/TR/baggage/>`_ HTTP headers for HTTP requests, but you can configure it to leverage different propagators. Here's
an example using Zipkin's `b3 propagation <https://github.com/openzipkin/b3-propagation>`_:

.. code-block:: sh

    pip install opentelemetry-propagator-b3

Following the installation of the package containing the b3 propagator, configure the propagator as follows:

.. code-block:: python

    from opentelemetry.propagate import set_global_textmap
    from opentelemetry.propagators.b3 import B3Format

    set_global_textmap(B3Format())

Use the OpenTelemetry Collector for traces
------------------------------------------

Although it's possible to directly export your telemetry data to specific backends, you might have more complex use cases such as the following:

* A single telemetry sink shared by multiple services, to reduce overhead of switching exporters.
* Aggregating traces across multiple services, running on multiple hosts.

To enable a broad range of aggregation strategies, OpenTelemetry provides the `opentelemetry-collector <https://github.com/open-telemetry/opentelemetry-collector>`_.
The Collector is a flexible application that can consume trace data and export to multiple other backends, including to another instance of the Collector.

Start the Collector locally to see how the Collector works in practice. Write the following file:

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

Then start the Docker container:

.. code-block:: sh

    docker run -p 55678:55678 \
        -v /tmp/otel-collector-config.yaml:/etc/otel-collector-config.yaml \
        omnition/opentelemetry-collector-contrib:latest \
        --config=/etc/otel-collector-config.yaml

Install the OpenTelemetry Collector exporter:

.. code-block:: sh

    pip install opentelemetry-exporter-otlp

Finally, execute the following script:

.. literalinclude:: getting_started/otlpcollector_example.py
    :language: python
    :lines: 15-
