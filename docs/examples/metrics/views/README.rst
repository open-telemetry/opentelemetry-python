View common scenarios
=====================

These examples show how to customize the metrics that are output by the SDK using Views. There are multiple examples:

* change_aggregation: Shows how to configure to change the default aggregation for an instrument.
* change_name: Shows how to change the name of a metric.
* limit_num_of_attrs: Shows how to limit the number of attributes that are output for a metric.
* drop_metrics_from_instrument: Shows how to drop measurements from an instrument.

The source files of these examples are available :scm_web:`here <docs/examples/metrics/views/>`.


Installation
------------

.. code-block:: sh

    pip install -r requirements.txt

Run the Example
---------------

.. code-block:: sh

    python <example_name>.py

The output will be shown in the console.

Useful links
------------

- OpenTelemetry_
- :doc:`../../api/metrics`

.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/
