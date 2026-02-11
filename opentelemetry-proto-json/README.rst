OpenTelemetry Python Proto JSON
================================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-proto-json.svg
   :target: https://pypi.org/project/opentelemetry-proto-json/

This library contains the generated code for OpenTelemetry protobuf data model with JSON encoding support. The code in the current package was generated using the v1.9.0 release_ of opentelemetry-proto and includes definitions for the OpenTelemetry JSON Protobuf encoding specification.

.. _release: https://github.com/open-telemetry/opentelemetry-proto/releases/tag/v1.9.0

Installation
------------

::

    pip install opentelemetry-proto-json

Code Generation
---------------

These files were generated automatically using the custom protoc plugin opentelemetry-codegen-json_ from code in opentelemetry-proto_.
To regenerate the code, run ``../scripts/proto_codegen_json.sh``.

To build against a new release or specific commit of opentelemetry-proto_,
update the ``PROTO_REPO_BRANCH_OR_COMMIT`` variable in
``../scripts/proto_codegen_json.sh``. Then run the script and commit the changes
as well as any fixes needed in the OTLP exporter.

.. _opentelemetry-codegen-json: https://github.com/open-telemetry/codegen/opentelemetry-codegen-json
.. _opentelemetry-proto: https://github.com/open-telemetry/opentelemetry-proto

References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
* `OpenTelemetry Proto <https://github.com/open-telemetry/opentelemetry-proto>`_
* `OTLP JSON Encoding Specification <https://opentelemetry.io/docs/specs/otlp/#json-protobuf-encoding>`_
