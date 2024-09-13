MetricReader configuration scenarios
====================================

These examples show how to customize the metrics that are output by the SDK using configuration on metric readers. There are multiple examples:

* preferred_aggregation.py: Shows how to configure the preferred aggregation for metric instrument types.
* preferred_temporality.py: Shows how to configure the preferred temporality for metric instrument types.
* preferred_exemplarfilter.py: Shows how to configure the exemplar filter.

The source files of these examples are available :scm_web:`here <docs/examples/metrics/reader/>`.


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
