View common scenarios
=====================

These examples show how to customize the metrics that are output by the SDK using Views. There are multiple examples:

* :scm_web:`change_aggregation.py <docs/examples/metrics/views/change_aggregation.py>`: Shows how to configure to change the default aggregation for an instrument.
* :scm_web:`change_name.py <docs/examples/metrics/views/change_name.py>`: Shows how to change the name of a metric.
* :scm_web:`limit_num_of_attrs.py <docs/examples/metrics/views/limit_num_of_attrs.py>`: Shows how to limit the number of attributes that are output for a metric.
* :scm_web:`drop_metrics_from_instrument.py <docs/examples/metrics/views/drop_metrics_from_instrument.py>`: Shows how to drop measurements from an instrument.
* :scm_web:`change_reservoir_factory.py <docs/examples/metrics/views/change_reservoir_factory.py>`: Shows how to use your own ``ExemplarReservoir``

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
- :doc:`../../../api/metrics`

.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/
