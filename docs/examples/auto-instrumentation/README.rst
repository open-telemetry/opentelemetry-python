Auto-instrumentation
====================

One of the best ways to instrument Python applications is to use OpenTelemetry automatic instrumentation (auto-instrumentation). This approach is simple, easy, and doesn't require many code changes. You only need to install a few Python packages to successfully instrument your application's code.

Overview
--------

This example demonstrates how to use auto-instrumentation in OpenTelemetry.
The example is based on a previous OpenTracing example that
you can find
`here <https://github.com/yurishkuro/opentracing-tutorial/tree/master/python>`__.

The source files for these examples are available `here <https://github.com/open-telemetry/opentelemetry-python/tree/main/docs/examples/auto-instrumentation>`__.

This example uses two different scripts. The main difference between them is
whether or not they're instrumented manually:

1. ``server_instrumented.py`` - instrumented manually
2. ``server_uninstrumented.py`` - not instrumented manually

Run the first script without the automatic instrumentation agent and
the second with the agent. They should both produce the same results, 
demonstrating that the automatic instrumentation agent does
exactly the same thing as manual instrumentation.

To better understand auto-instrumentation, see the relevant part of both scripts:

Manually instrumented server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``server_instrumented.py``

.. code:: python

    @app.route("/server_request")
    def server_request():
        with tracer.start_as_current_span(
            "server_request",
            context=extract(request.headers),
            kind=trace.SpanKind.SERVER,
            attributes=collect_request_attributes(request.environ),
        ):
            print(request.args.get("param"))
            return "served"

Server not instrumented manually
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``server_uninstrumented.py``

.. code:: python

    @app.route("/server_request")
    def server_request():
        print(request.args.get("param"))
        return "served"

Prepare
-------

Execute the following example in a separate virtual environment.
Run the following commands to prepare for auto-instrumentation:

.. code:: sh

    $ mkdir auto_instrumentation
    $ virtualenv auto_instrumentation
    $ source auto_instrumentation/bin/activate

Install
-------

Run the following commands to install the appropriate packages. The
``opentelemetry-instrumentation`` package provides several 
commands that help automatically instruments a program.

.. code:: sh

    $ pip install opentelemetry-sdk
    $ pip install opentelemetry-instrumentation
    $ pip install opentelemetry-instrumentation-flask
    $ pip install requests

Execute
---------

This section guides you through the manual process of instrumenting
a server as well as the process of executing an automatically 
instrumented server.

Execute a manually instrumented server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute the server in two separate consoles, one to run each of the 
scripts that make up this example:

.. code:: sh

    $ source auto_instrumentation/bin/activate
    $ python server_instrumented.py

.. code:: sh

    $ source auto_instrumentation/bin/activate
    $ python client.py testing

When you execute ``server_instrumented.py`` it returns a JSON response
similar to the following example:

.. code:: sh

    {
        "name": "server_request",
        "context": {
            "trace_id": "0xfa002aad260b5f7110db674a9ddfcd23",
            "span_id": "0x8b8bbaf3ca9c5131",
            "trace_state": "{}"
        },
        "kind": "SpanKind.SERVER",
        "parent_id": null,
        "start_time": "2020-04-30T17:28:57.886397Z",
        "end_time": "2020-04-30T17:28:57.886490Z",
        "status": {
            "status_code": "OK"
        },
        "attributes": {
            "http.method": "GET",
            "http.server_name": "127.0.0.1",
            "http.scheme": "http",
            "host.port": 8082,
            "http.host": "localhost:8082",
            "http.target": "/server_request?param=testing",
            "net.peer.ip": "127.0.0.1",
            "net.peer.port": 52872,
            "http.flavor": "1.1"
        },
        "events": [],
        "links": [],
        "resource": {
            "telemetry.sdk.language": "python",
            "telemetry.sdk.name": "opentelemetry",
            "telemetry.sdk.version": "0.16b1"
        }
    }

Execute an automatically instrumented server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Stop the execution of ``server_instrumented.py`` with ``ctrl + c``
and run the following command instead:

.. code:: sh

    $ opentelemetry-instrument --trace-exporter console_span python server_uninstrumented.py

In the console where you previously executed ``client.py``, run the following
command again:

.. code:: sh

    $ python client.py testing

When you execute ``server_uninstrumented.py`` it returns a JSON response
similar to the following example:

.. code:: sh

    {
        "name": "server_request",
        "context": {
            "trace_id": "0x9f528e0b76189f539d9c21b1a7a2fc24",
            "span_id": "0xd79760685cd4c269",
            "trace_state": "{}"
        },
        "kind": "SpanKind.SERVER",
        "parent_id": "0xb4fb7eee22ef78e4",
        "start_time": "2020-04-30T17:10:02.400604Z",
        "end_time": "2020-04-30T17:10:02.401858Z",
        "status": {
            "status_code": "OK"
        },
        "attributes": {
            "http.method": "GET",
            "http.server_name": "127.0.0.1",
            "http.scheme": "http",
            "host.port": 8082,
            "http.host": "localhost:8082",
            "http.target": "/server_request?param=testing",
            "net.peer.ip": "127.0.0.1",
            "net.peer.port": 48240,
            "http.flavor": "1.1",
            "http.route": "/server_request",
            "http.status_text": "OK",
            "http.status_code": 200
        },
        "events": [],
        "links": [],
        "resource": {
        "telemetry.sdk.language": "python",
        "telemetry.sdk.name": "opentelemetry",
        "telemetry.sdk.version": "0.16b1",
        "service.name": ""
        }
    }

You can see that both outputs are the same because automatic instrumentation does
exactly what manual instrumentation does.

Instrumentation while debugging
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The debug mode can be enabled in the Flask app like this:


.. code:: python

    if __name__ == "__main__":
        app.run(port=8082, debug=True)

The debug mode can break instrumentation from happening because it enables a
reloader. To run instrumentation while the debug mode is enabled, set the
``use_reloader`` option to ``False``:

.. code:: python

    if __name__ == "__main__":
        app.run(port=8082, debug=True, use_reloader=False)


Additional resources 
~~~~~~~~~~~~~~~~~~~~

In order to send telemetry to an OpenTelemetry Collector without doing any
additional configuration, read about the `OpenTelemetry Distro <../distro/README.html>`_
package.
