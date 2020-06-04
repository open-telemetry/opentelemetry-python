Cloud Trace Exporter Example
============================

These examples show how to use OpenTelemetry to send tracing data to Cloud Trace.


Basic Example
-------------

To use this exporter you first need to:
    * A Google Cloud project. You can `create one here. <https://console.cloud.google.com/projectcreate>`_
    * Enable Cloud Trace API (aka StackDriver Trace API) in the project `here. <https://console.cloud.google.com/apis/library?q=cloud_trace>`_
    * Enable `Default Application Credentials. <https://developers.google.com/identity/protocols/application-default-credentials>`_

* Installation

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk
    pip install opentelemetry-exporter-cloud-trace

* Run example

.. code-block:: sh

    python basic_trace.py

Checking Output
--------------------------

After running any of these examples, you can go to `Cloud Trace overview <https://console.cloud.google.com/traces/list>`_ to see the results.

* `More information about exporters in general <https://opentelemetry-python.readthedocs.io/en/stable/getting-started.html#configure-exporters-to-emit-spans-elsewhere>`_