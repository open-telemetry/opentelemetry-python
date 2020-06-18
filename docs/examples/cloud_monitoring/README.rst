Cloud Monitoring Exporter Example
=================================

These examples show how to use OpenTelemetry to send metrics data to Cloud Monitoring.


Basic Example
-------------

To use this exporter you first need to:
    * `Create a Google Cloud project <https://console.cloud.google.com/projectcreate>`_.
    * Enable the Cloud Monitoring API (aka Stackdriver Monitoring API) in the project `here <https://console.cloud.google.com/apis/library?q=cloud_monitoring>`_.
    * Enable `Default Application Credentials <https://developers.google.com/identity/protocols/application-default-credentials>`_.

* Installation

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk
    pip install opentelemetry-exporter-cloud-monitoring

* Run example

.. literalinclude:: basic_metrics.py
    :language: python
    :lines: 1-

Viewing Output
--------------------------

After running the example:
    * Go to the `Cloud Monitoring Metrics Explorer page <https://console.cloud.google.com/monitoring/metrics-explorer>`_.
    * In "Find resource type and metric" enter "OpenTelemetry/request_counter".
    * You can filter by labels and change the graphical output here as well.

Troubleshooting
--------------------------

``One or more points were written more frequently than the maximum sampling period configured for the metric``
##############################################################################################################

Currently, Cloud Monitoring allows one write per second for any unique tuple (metric_name, metric_label_value_1, metric_label_value_2, ...). The exporter should rate limit on its own but issues arise if:

    * You are restarting the server more then once every 10 seconds. Either wait longer or ignore the errors.
    * You have a multiple exporters (possibly on different threads) writing to the same tuple. You need to add ``add_unique_identifier=True`` to the CloudMonitoringMetricsExporter constructor. This adds a UUID label_value, making the tuple unique again.
