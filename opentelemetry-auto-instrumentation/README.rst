OpenTelemetry Auto Instrumentation
============================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-auto-instrumentation.svg
   :target: https://pypi.org/project/opentelemetry-auto-instrumentation/

Installation
------------

::

    pip install opentelemetry-auto-instrumentation

References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_

Usage
-----

This package provides a command that automatically instruments a program:

::

    opentelemetry-auto-instrumentation program.py

The code in ``program.py`` needs to use one of the packages for which there is
an OpenTelemetry extension. For a list of the available extensions please check
`here <https://opentelemetry-python.readthedocsio/>`_.
