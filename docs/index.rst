OpenTelemetry Python
====================

Welcome to OpenTelemetry Python documentation!

This documentation describes the ``opentelemetry-api``, ``opentelemetry-sdk``
and integration packages.

TODO: intro with link to opentelemetry.io

Installation
------------

This repository includes multiple installable packages. The ``opentelemetry-api``
package includes abstract classes and no-op implementations that comprise the OpenTelemetry API following
`the specification <https://github.com/open-telemetry/opentelemetry-specification>`_.
The ``opentelemetry-sdk`` package is the reference implementation of the API.

Libraries that produce telemetry data should only depend on ``opentelemetry-api``,
and defer the choice of the SDK to the application developer. Applications may
depend on ``opentelemetry-sdk`` or another package that implements the API.

**Please note** that this library is currently in _alpha_, and shouldn't be
used in production environments.

The API and SDK packages are available on PyPI, and can installed via ``pip``:

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk


Different integration packages can be installed separately as:

.. code-block:: sh

    pip install opentelemetry-ext-{integration}


To install the development versions of these packages instead, clone or fork
this repo and do an `editable
install <https://pip.pypa.io/en/stable/reference/pip_install/#editable-installs>`_:

.. code-block:: sh

    pip install -e ./opentelemetry-api
    pip install -e ./opentelemetry-sdk
    pip install -e ./ext/opentelemetry-ext-{integration}


Examples
--------

TODO: Link to complete and better examples
The following are two basic examples. For a most complex examples please see.

Tracing
*******

.. literalinclude:: trace_example.py
  :language: python

Metrics
*******

.. literalinclude:: metrics_example.py
  :language: python

.. toctree::
    :maxdepth: 1
    :caption: OpenTelemetry Python Packages

    api/api
    sdk/sdk

.. toctree::
    :maxdepth: 1
    :caption: OpenTelemetry Integrations

    ext/flask/flask
    ext/http_requests/http_requests
    ext/jaeger/jaeger
    ext/opentracing_shim/opentracing_shim
    ext/pymongo/pymongo
    ext/wsgi/wsgi

.. toctree::
    :maxdepth: 1
    :caption: Examples

    examples/index

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
