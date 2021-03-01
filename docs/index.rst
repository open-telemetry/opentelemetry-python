OpenTelemetry-Python
====================

The Python `OpenTelemetry <https://opentelemetry.io/>`_ client.

.. image:: https://img.shields.io/badge/slack-chat-green.svg
   :target: https://cloud-native.slack.com/archives/C01PD4HUVBL
   :alt: Slack Chat


This documentation describes the :doc:`opentelemetry-api <api/api>`,
:doc:`opentelemetry-sdk <sdk/sdk>`, and several `integration packages <#integrations>`_.

**Please note** that this library is currently in _beta_, and shouldn't
generally be used in production environments.

Requirement
-----------
OpenTelemetry-Python supports Python 3.5 and higher.

Installation
------------

The API and SDK packages are available on PyPI, and can installed via pip:

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk

In addition, there are several extension packages which can be installed separately as::

    pip install opentelemetry-exporter-{exporter}
    pip install opentelemetry-instrumentation-{instrumentation}

These are for exporter and instrumentation packages respectively.
Some packages can be found in :scm_web:`instrumentation <instrumentation/>` and :scm_web:`exporter <exporter/>`
directory of the repository. The remaining packages can be found at the 
`Contrib repo instrumentation <https://github.com/open-telemetry/opentelemetry-python-contrib/tree/main/instrumentation>`_
and `Contrib repo exporter <https://github.com/open-telemetry/opentelemetry-python-contrib/tree/main/exporter>`_ directories.

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


.. toctree::
    :maxdepth: 1
    :caption: Getting Started
    :name: getting-started

    getting-started
    faq-and-cookbook

.. toctree::
    :maxdepth: 1
    :caption: OpenTelemetry Python Packages
    :name: packages

    api/api
    sdk/sdk

.. toctree::
    :maxdepth: 2
    :caption: OpenTelemetry Exporters
    :name: exporters
    :glob:

    exporter/**

.. toctree::
    :maxdepth: 2
    :caption: OpenTelemetry Shims
    :name: Shims
    :glob:

    shim/**

.. toctree::
    :maxdepth: 1
    :caption: OpenTelemetry Python Performance
    :name: performance-tests
    :glob:

    performance/**

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
