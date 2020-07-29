OpenTelemetry-Python
====================

The Python `OpenTelemetry <https://opentelemetry.io/>`_ client.

.. image:: https://img.shields.io/gitter/room/opentelemetry/opentelemetry-python
   :target: https://gitter.im/open-telemetry/opentelemetry-python
   :alt: Gitter Chat


This documentation describes the :doc:`opentelemetry-api <api/api>`,
:doc:`opentelemetry-sdk <sdk/sdk>`, and several `integration packages <#integrations>`_.

**Please note** that this library is currently in alpha, and shouldn't be
used in production environments.

Installation
------------

The API and SDK packages are available on PyPI, and can installed via pip:

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk

In addition, there are several extension packages which can be installed separately as::

    pip install opentelemetry-ext-{integration}

The extension packages can be found in :scm_web:`ext/ directory of the repository <ext/>`.

Extensions
----------

Visit `OpenTelemetry Registry <https://opentelemetry.io/registry/?s=python>`_ to find
related projects like exporters, instrumentation libraries, tracer implementations, etc.

Installing Cutting Edge Packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

While the project is pre-1.0, there may be significant functionality that
has not yet been released to PyPI. In that situation, you may want to
install the packages directly from the repo. This can be done by cloning the
repository and doing an `editable
install <https://pip.pypa.io/en/stable/reference/pip_install/#editable-installs>`_:

.. code-block:: sh

    git clone https://github.com/open-telemetry/opentelemetry-python.git
    cd opentelemetry-python
    pip install -e ./opentelemetry-api
    pip install -e ./opentelemetry-sdk
    pip install -e ./ext/opentelemetry-ext-{integration}


.. toctree::
    :maxdepth: 1
    :caption: Getting Started
    :name: getting-started

    getting-started

.. toctree::
    :maxdepth: 1
    :caption: OpenTelemetry Python Packages
    :name: packages

    api/api
    sdk/sdk
    instrumentation/instrumentation

.. toctree::
    :maxdepth: 2
    :caption: OpenTelemetry Exporters
    :name: exporters
    :glob:

    exporter/**

.. toctree::
    :maxdepth: 2
    :caption: OpenTelemetry Instrumentations
    :name: Instrumentations
    :glob:

    ext/**

.. toctree::
    :maxdepth: 1
    :caption: Examples
    :name: examples
    :glob:

    examples/**

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
