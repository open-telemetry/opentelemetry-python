Datadog Exporter Example
=======================

This example shows how to use OpenTelemetry to send tracing data to Datadog.

Installation
------------

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk
    pip install opentelemetry-ext-datadog

Basic Example
-------------

* Start Datadog Agent

.. code-block:: sh

    docker run -d -v /var/run/docker.sock:/var/run/docker.sock:ro \
        -v /proc/:/host/proc/:ro \
        -v /sys/fs/cgroup/:/host/sys/fs/cgroup:ro \
        -p 127.0.0.1:8126:8126/tcp \
        -e DD_API_KEY="<DATADOG_API_KEY>" \
        -e DD_APM_ENABLED=true \
        datadog/agent:latest

* Run example

.. code-block:: sh

    python datadog_exporter.py

Auto-Instrumention Example
--------------------------

* Start Datadog Agent (same as above)

* Install libraries

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk
    pip install opentelemetry-ext-datadog
    pip install opentelemetry-auto-instrumentation
    pip install opentelemetry-ext-flask
    pip install flask
    pip install requests

* Run auto-instrumentation example

.. code-block:: sh
    # start server in a terminal
    opentelemetry-auto-instrumentation server.py
    # run client in another terminal
    python client.py testing
    # run client to force server error
    python client.py error
