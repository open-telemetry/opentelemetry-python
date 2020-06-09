Cloud Trace Exporter Example
============================

These examples show how to use OpenTelemetry to send tracing data to Cloud Trace.


Basic Example
-------------

To use this exporter you first need to:
    * A Google Cloud project. You can `create one here. <https://console.cloud.google.com/projectcreate>`_
    * Enable Cloud Trace API (aka Stackdriver Trace API) in the project `here. <https://console.cloud.google.com/apis/library?q=cloud_trace>`_
    * Enable `Default Application Credentials. <https://developers.google.com/identity/protocols/application-default-credentials>`_

* Installation

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk
    pip install opentelemetry-exporter-cloud-trace

* Run example locally

.. code-block:: sh

    cd opentelemetry-python/docs/examples/cloud_trace_exporter
    python basic_trace.py

Checking Output
--------------------------

After running any of these examples, you can go to `Cloud Trace overview <https://console.cloud.google.com/traces/list>`_ to see the results.


Further Reading
--------------------------

* `More information about exporters in general <https://opentelemetry-python.readthedocs.io/en/stable/getting-started.html#configure-exporters-to-emit-spans-elsewhere>`_

Troubleshooting
--------------------------

Running basic_trace.py hangs:
    * Make sure you've setup Application Default Credentials. Either run ``gcloud auth application-default login`` or set the ``GOOGLE_APPLICATION_CREDENTIALS`` environment variable to be a path to a service account token file.
Getting error ``google.api_core.exceptions.ResourceExhausted: 429 Resource has been exhausted``:
    * Check that you've enabled the `Cloud Trace (Stackdriver Trace) API <https://console.cloud.google.com/apis/library?q=cloud_trace>`_