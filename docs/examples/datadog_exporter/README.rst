Datadog Exporter Example
========================

These examples show how to use OpenTelemetry to send tracing data to Datadog.


Basic Example
-------------

* Installation

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk
    pip install opentelemetry-exporter-datadog

* Start Datadog Agent

.. code-block:: sh

    docker run --rm \
        -v /var/run/docker.sock:/var/run/docker.sock:ro \
        -v /proc/:/host/proc/:ro \
        -v /sys/fs/cgroup/:/host/sys/fs/cgroup:ro \
        -p 127.0.0.1:8126:8126/tcp \
        -e DD_API_KEY="<DATADOG_API_KEY>" \
        -e DD_APM_ENABLED=true \
        datadog/agent:latest

* Run example

.. code-block:: sh

    python basic_example.py


.. code-block:: sh

    python basic_example.py

Distributed Example
-------------------

* Installation

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk
    pip install opentelemetry-exporter-datadog
    pip install opentelemetry-instrumentation
    pip install opentelemetry-ext-flask
    pip install flask
    pip install requests

* Start Datadog Agent

.. code-block:: sh

    docker run --rm \
        -v /var/run/docker.sock:/var/run/docker.sock:ro \
        -v /proc/:/host/proc/:ro \
        -v /sys/fs/cgroup/:/host/sys/fs/cgroup:ro \
        -p 127.0.0.1:8126:8126/tcp \
        -e DD_API_KEY="<DATADOG_API_KEY>" \
        -e DD_APM_ENABLED=true \
        datadog/agent:latest

* Start server

.. code-block:: sh

    opentelemetry-instrument python server.py

* Run client

.. code-block:: sh

    opentelemetry-instrument python client.py testing

* Run client with parameter to raise error

.. code-block:: sh

    opentelemetry-instrument python client.py error

* Run Datadog instrumented client

The OpenTelemetry instrumented server is set up with propagation of Datadog trace context.

.. code-block:: sh

    pip install ddtrace
    ddtrace-run python datadog_client.py testing
