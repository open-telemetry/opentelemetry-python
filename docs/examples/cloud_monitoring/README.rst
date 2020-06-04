Cloud Monitoring Exporter Example
=================================

These examples show how to use OpenTelemetry to send metrics data to Cloud Monitoring.


Basic Example
-------------

To use this exporter you first need to:
    * A Google Cloud project. You can `create one here <https://console.cloud.google.com/projectcreate>`_.
    * Enable the Cloud Monitoring API (aka Stackdriver Monitoring API) in the project `here <https://console.cloud.google.com/apis/library?q=cloud_monitoring>`_.
    * Enable `Default Application Credentials <https://developers.google.com/identity/protocols/application-default-credentials>`_.

* Installation

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk
    pip install opentelemetry-exporter-cloud-monitoring

* Run example

.. code-block:: sh

    python basic_metrics.py

Viewing Output
--------------------------

After running the example:
    * Go to `Cloud Monitoring Metrics Explorer page <https://console.cloud.google.com/monitoring/metrics-explorer>`_.
    * In "Find resource type and metric" enter "OpenTelemetry/request_counter".
    * You can filter by labels and change the graphical output here as well.