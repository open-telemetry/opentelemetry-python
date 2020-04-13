Datadog Exporter Example
=======================

This example shows how to use OpenTelemetry to send tracing data to Datadog.

Installation
------------

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk
    pip install opentelemetry-ext-datadog

Run the Example
---------------

* Start Datadog Agent

.. code-block:: sh

    docker run -d -v /var/run/docker.sock:/var/run/docker.sock:ro \
        -v /proc/:/host/proc/:ro \
        -v /sys/fs/cgroup/:/host/sys/fs/cgroup:ro \
        -p 127.0.0.1:8126:8126/tcp \
        -e DD_API_KEY="<DATADOG_API_KEY>" \
        -e DD_APM_ENABLED=true \
        datadog/agent:latest

* Run the example

.. code-block:: sh

    python datadog_exporter.py

The traces will be available at http://datadoghq.com/.
