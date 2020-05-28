Cloud Trace Exporter Example
============================

These examples show how to use OpenTelemetry to send tracing data to Cloud Trace.


Basic Example
-------------

To use this exporter you first need to:
    * A Google Cloud project. You can `create one here. <https://console.cloud.google.com/projectcreate>`_
    * Enable Cloud Monitoring API (aka StackDriver Monitoring API) in the project `here. <https://console.cloud.google.com/apis/library?q=cloud_monitoring>`_
    * Enable `Default Application Credentials. <https://developers.google.com/identity/protocols/application-default-credentials>`_

* Installation

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk
    pip install opentelemetry-ext-cloud-monitoring

* Run example

.. code-block:: sh

    python basic_metrics.py

Checking Output
--------------------------

After running any of these examples, to see the results
    * Go to `Cloud Monitoring overview <https://console.cloud.google.com/monitoring/metrics-explorer>`_ to see the results.
    * In "Find resource type and metric" enter "OpenTelemetry/<your_metric_name"
    * You can filter by labels and change the graphical output here as well