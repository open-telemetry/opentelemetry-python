OpenTelemetry Prometheus Exporter
=================================

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

    from opentelemetry import metrics
    from opentelemetry.ext.prometheus import PrometheusMetricsExporter
    from opentelemetry.sdk.metrics import Counter, Meter
    from opentelemetry.sdk.metrics.export.controller import PushController
    from prometheus_client import start_http_server

    # Start Prometheus client
    start_http_server(port=8000, addr="localhost")

    # Meter is responsible for creating and recording metrics
    metrics.set_preferred_meter_implementation(lambda _: Meter())
    meter = metrics.meter()
    # exporter to export metrics to Prometheus
    prefix = "MyAppPrefix"
    exporter = PrometheusMetricsExporter(prefix)
    # controller collects metrics created from meter and exports it via the
    # exporter every interval
    controller = PushController(meter, exporter, 5)

    counter = meter.create_metric(
        "requests",
        "number of requests",
        "requests",
        int,
        Counter,
        ("environment",),
    )

    # Labelsets are used to identify key-values that are associated with a specific
    # metric that you want to record. These are useful for pre-aggregation and can
    # be used to store custom dimensions pertaining to a metric
    label_set = meter.get_label_set({"environment": "staging"})

    counter.add(25, label_set)
    input("Press any key to exit...")



References
----------

* `Prometheus <https://prometheus.io/>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
