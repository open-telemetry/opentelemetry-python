MetricReader configuration scenarios
====================================

These examples show how to customize the metrics that are output by the SDK using configuration on metric readers. There are multiple examples:

* :scm_web:`preferred_aggregation.py <docs/examples/metrics/reader/preferred_aggregation.py>`: Shows how to configure the preferred aggregation for metric instrument types.
* :scm_web:`preferred_temporality.py <docs/examples/metrics/reader/preferred_temporality.py>`: Shows how to configure the preferred temporality for metric instrument types.
* :scm_web:`preferred_exemplarfilter.py <docs/examples/metrics/reader/preferred_exemplarfilter.py>`: Shows how to configure the exemplar filter.
* :scm_web:`synchronous_gauge_read.py <docs/examples/metrics/reader/synchronous_gauge_read.py>`: Shows how to use `PeriodicExportingMetricReader` in a synchronous manner to explicitly control the collection of metrics.

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
