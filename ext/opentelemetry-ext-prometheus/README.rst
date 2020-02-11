OpenTelemetry Prometheus Exporter
=============================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-ext-prometheus.svg
   :target: https://pypi.org/project/opentelemetry-ext-prometheus/

This library allows to export metrics data to `Prometheus <https://prometheus.io/>`_.

Installation
------------

::

     pip install opentelemetry-ext-prometheus


Usage
-----

The **OpenTelemetry Prometheus Exporter** allows to export `OpenTelemetry`_ metrics to `Prometheus`_.


.. _Prometheus: https://prometheus.io/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/

.. code:: python

    import time

    from opentelemetry import metrics
    from opentelemetry.ext.prometheus import PrometheusMetricsExporter
    from opentelemetry.sdk.metrics import Counter, Meter
    from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter
    from opentelemetry.sdk.metrics.export.controller import PushController

    # Meter is responsible for creating and recording metrics
    meter = Meter()
    metrics.set_preferred_meter_implementation(meter)
    # exporter to export metrics to Prometheus
    port = 8000
    address = "localhost"
    prefix = "MyAppPrefix"
    exporter = PrometheusMetricsExporter(port, address, prefix)
    # controller collects metrics created from meter and exports it via the
    # exporter every interval
    controller = PushController(meter, exporter, 5)

    counter = meter.create_metric(
        "available memory",
        "available memory",
        "bytes",
        int,
        Counter,
        ("environment",),
    )
    
    # Labelsets are used to identify key-values that are associated with a specific
    # metric that you want to record. These are useful for pre-aggregation and can
    # be used to store custom dimensions pertaining to a metric
    label_set = meter.get_label_set({"environment": "staging"})

    counter.add(25, label_set)
    # We sleep for 5 seconds, exported value should be 25
    time.sleep(5)


References
----------

* `Prometheus <https://prometheus.io/>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
