OpenTelemetry Python SDK
============================================================================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-sdk.svg
   :target: https://pypi.org/project/opentelemetry-sdk/

Installation
------------

::

    pip install opentelemetry-sdk

Running Performance Tests
-------------------------

Running resource usage tests:

1. Install scalene using the following command

::

    pip install -U scalene

2. Run the `scalene` tests using

::

    scalene opentelemetry-sdk/tests/performance/resource-usage/trace/profile_resource_usage_<NAME_OF_TEST>.py

References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
