OpenTelemetry Instrumentation
=============================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-instrumentation.svg
   :target: https://pypi.org/project/opentelemetry-instrumentation/

Installation
------------

::

    pip install opentelemetry-instrumentation


This package provides a couple of commands that help automatically instruments a program:

opentelemetry-instrument
------------------------

::

    opentelemetry-instrument python program.py

The code in ``program.py`` needs to use one of the packages for which there is
an OpenTelemetry integration. For a list of the available integrations please
check `here <https://opentelemetry-python.readthedocs.io/en/stable/index.html#integrations>`_


opentelemetry-bootstrap
-----------------------

::

    opentelemetry-bootstrap --action=install|requirements

This commands inspects the active Python site-packages and figures out which
instrumentation packages the user might want to install. By default it prints out
a list of the suggested instrumentation packages which can be added to a requirements.txt
file. It also supports installing the suggested packages when run with :code:`--action=install`
flag.

References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
