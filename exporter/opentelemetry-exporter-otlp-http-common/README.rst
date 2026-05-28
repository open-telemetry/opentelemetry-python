OpenTelemetry OTLP HTTP Common
===============================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-exporter-otlp-http-common.svg
   :target: https://pypi.org/project/opentelemetry-exporter-otlp-http-common/

OpenTelemetry OTLP HTTP export utilities.

This package is intended to be used by OpenTelemetry signal exporters (traces, metrics,
logs) that send telemetry over OTLP/HTTP. Currently, all functionality in this package
is marked as internal and is not intended for use directly by application developers.

Installation
------------

::

    pip install opentelemetry-exporter-otlp-http-common

Usage
-----

``OTLPHTTPClient`` wraps a transport and handles retry and compression. Pass it a
transport and an endpoint, then call ``export()`` with a serialized OTLP payload::

    from opentelemetry.exporter.http.transport._requests import RequestsHTTPTransport
    from opentelemetry.exporter.otlp.http.common._otlp_client import (
        Compression,
        OTLPHTTPClient,
    )

    transport = RequestsHTTPTransport()
    client = OTLPHTTPClient(
        transport=transport,
        endpoint="http://localhost:4318/v1/traces",
        kind="spans",
        compression=Compression.GZIP,
    )

    result = client.export(serialized_bytes)
    if not result.success:
        print(f"Export failed: {result.status_code} {result.reason}")

    client.close()

References
----------

* `OpenTelemetry <https://opentelemetry.io/>`_
* `OTLP Specification <https://opentelemetry.io/docs/specs/otlp/>`_
* `opentelemetry-exporter-http-transport <https://pypi.org/project/opentelemetry-exporter-http-transport/>`_
