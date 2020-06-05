Datadog Exporter Example
========================

These examples show how to use OpenTelemetry to send tracing data to Datadog.


Basic Example
-------------

* Installation

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk
    pip install opentelemetry-ext-datadog

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

    python datadog_exporter.py

Auto-Instrumention Example
--------------------------

* Installation

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk
    pip install opentelemetry-ext-datadog
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

    opentelemetry-instrumentation python server.py

* Run client

.. code-block:: sh

    opentelemetry-instrumentation python client.py testing

* Run client with parameter to raise error

.. code-block:: sh

    opentelemetry-instrumentation python client.py error
