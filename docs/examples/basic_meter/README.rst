Basic Meter
===========

These examples show how to use OpenTelemetry to capture and report metrics.

There are three different examples:

* basic_metrics: Shows how to create a metric instrument, how to configure an
  exporter and a controller and also how to capture data by using the direct
  calling convention.

* calling_conventions: Shows how to use the direct, bound and batch calling conventions.

* observer: Shows how to use the observer instrument.

The source files of these examples are available :scm_web:`here <docs/examples/basic_meter/>`.

Installation
------------

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk
    pip install psutil # needed to get ram and cpu usage in the observer example

Run the Example
---------------

.. code-block:: sh

    python <example_name>.py

The output will be shown in the console after few seconds.

Useful links
------------

- OpenTelemetry_
- :doc:`../../api/metrics`

.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/
