OpenTelemetry Python Proto
==========================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-proto.svg
   :target: https://pypi.org/project/opentelemetry-proto/

Installation
------------

::

    pip install opentelemetry-proto

Code Generation
---------------

These files were generated automatically from code in opentelemetry-proto_.
To regenerate the code, run ``../scripts/proto_codegen.sh``.

To build against a new release or specific commit of opentelemetry-proto_,
update the ``PROTO_REPO_BRANCH_OR_COMMIT`` variable in
``../scripts/proto_codegen.sh``. Then run the script and commit the changes
as well as any fixes needed in the OTLP exporter.

.. _opentelemetry-proto: https://github.com/open-telemetry/opentelemetry-proto


References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
* `OpenTelemetry Proto <https://github.com/open-telemetry/opentelemetry-proto>`_
* `proto_codegen.sh script <https://github.com/open-telemetry/opentelemetry-python/blob/master/scripts/proto_codegen.sh>`_
