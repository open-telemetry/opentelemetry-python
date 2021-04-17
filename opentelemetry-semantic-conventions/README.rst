OpenTelemetry Python Semantic Conventions
=========================================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-semantic-conventions.svg
   :target: https://pypi.org/project/opentelemetry-semantic-conventions/

Installation
------------

::

    pip install opentelemetry-semantic-conventions

Code Generation
---------------

These files were generated automatically from code in opentelemetry-semantic-conventions_.
To regenerate the code, run ``../scripts/semconv/generate.sh``.

To build against a new release or specific commit of opentelemetry-semantic-conventions_,
update the ``SPEC_VERSION`` variable in
``../scripts/semconv/generate.sh``. Then run the script and commit the changes.

.. _opentelemetry-semantic-conventions: https://github.com/open-telemetry/opentelemetry-semantic-conventions


References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
* `OpenTelemetry Semantic Conventions YAML Definitions <https://github.com/open-telemetry/opentelemetry-specification/tree/main/semantic_conventions>`_
* `generate.sh script <https://github.com/open-telemetry/opentelemetry-python/blob/main/scripts/semconv/generate.sh>`_
