Prometheus Instrumentation
==========================

This shows how to use ``opentelemetry-exporter-prometheus`` to automatically generate Prometheus metrics.

The source files of these examples are available :scm_web:`here <docs/examples/prometheus-grafana/>`.

Preparation
-----------

This example will be executed in a separate virtual environment:

.. code-block::

    $ mkdir prometheus_auto_instrumentation
    $ virtualenv prometheus_auto_instrumentation
    $ source prometheus_auto_instrumentation/bin/activate


Installation
------------

.. code-block::

    $ pip install -r requirements.txt


Execution
---------

.. code-block::

    $ python ./prometheus-monitor.py
    $ Server is running at http://localhost:8000

Now you can visit http://localhost:8000/metrics to see Prometheus metrics. 
You should see something like:

.. code-block::

    # HELP python_gc_objects_collected_total Objects collected during gc
    # TYPE python_gc_objects_collected_total counter
    python_gc_objects_collected_total{generation="0"} 320.0
    python_gc_objects_collected_total{generation="1"} 58.0
    python_gc_objects_collected_total{generation="2"} 0.0
    # HELP python_gc_objects_uncollectable_total Uncollectable objects found during GC
    # TYPE python_gc_objects_uncollectable_total counter
    python_gc_objects_uncollectable_total{generation="0"} 0.0
    python_gc_objects_uncollectable_total{generation="1"} 0.0
    python_gc_objects_uncollectable_total{generation="2"} 0.0
    # HELP python_gc_collections_total Number of times this generation was collected
    # TYPE python_gc_collections_total counter
    python_gc_collections_total{generation="0"} 61.0
    python_gc_collections_total{generation="1"} 5.0
    python_gc_collections_total{generation="2"} 0.0
    # HELP python_info Python platform information
    # TYPE python_info gauge
    python_info{implementation="CPython",major="3",minor="8",patchlevel="5",version="3.8.5"} 1.0
    # HELP MyAppPrefix_my_counter_total 
    # TYPE MyAppPrefix_my_counter_total counter
    MyAppPrefix_my_counter_total 964.0
 
``MyAppPrefix_my_counter_total`` is the custom counter created in the application with the custom prefix ``MyAppPrefix``.
