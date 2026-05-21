Rolldice — OpenTelemetry Reference Application (FastAPI)
=========================================================

This is the Python/FastAPI implementation of the
`OpenTelemetry reference application specification <https://opentelemetry.io/docs/getting-started/reference-application-specification/>`_.

It demonstrates all four OpenTelemetry signal types in a single service:

* **Traces** — automatic HTTP spans via ``FastAPIInstrumentor``, plus manual
  child spans for the dice-rolling business logic.
* **Metrics** — a call counter, an outcome histogram, and an observable gauge,
  defined in the library using only the OTel API.
* **Logs** — structured log records emitted through Python's ``logging`` module
  and forwarded to OpenTelemetry via ``LoggingHandler`` (the log bridge).
* **Resources** — process and environment metadata attached automatically via
  resource detectors.

Architecture
------------

The code is split into two modules to illustrate the recommended library/application boundary:

``library/rolldice.py``
    Dice logic.  Imports only from ``opentelemetry`` (the API package) — **no**
    SDK imports.  This makes the library usable in any application regardless
    of which SDK implementation is chosen.

``otel-config.yaml``
    Declarative configuration file.  Defines the trace, metric, and log
    pipelines (exporters, processors, samplers, resource detectors) in a YAML
    file following the `OpenTelemetry Configuration Schema
    <https://github.com/open-telemetry/opentelemetry-configuration>`_.  This
    replaces programmatic SDK initialization and allows operators to change
    telemetry behavior without modifying code.

``app/telemetry.py``
    SDK initialization.  Loads ``otel-config.yaml`` using the SDK's file
    configuration API and installs the configured providers globally.  Also
    sets up the Python logging bridge (``LoggingHandler``), which is not
    covered by the config schema.

``app/main.py``
    FastAPI application.  Imports ``app.telemetry`` first, then creates the
    ``FastAPI`` app, instruments it, and defines the ``/rolldice`` endpoint.

Prerequisites
-------------

* Python ≥ 3.12
* ``pip`` or ``uv``

Install
-------

.. code-block:: bash

   cd instrumentation/opentelemetry-instrumentation-fastapi/examples/rolldice
   pip install .

Run
---

.. code-block:: bash

   uvicorn app.main:app --host 0.0.0.0 --port 8080

Or directly:

.. code-block:: bash

   python -m app.main

The server listens on port 8080 by default.  Set ``APPLICATION_PORT`` to use a
different port.

Test the API
------------

.. code-block:: bash

   # Single roll (default) — returns a number, e.g. "4"
   curl "http://localhost:8080/rolldice"

   # Five rolls — returns a JSON array, e.g. [3, 5, 2, 6, 1]
   curl "http://localhost:8080/rolldice?rolls=5"

   # With a player name (shown in DEBUG logs)
   curl "http://localhost:8080/rolldice?rolls=3&player=Alice"

   # Invalid input — returns HTTP 400 with error JSON
   curl "http://localhost:8080/rolldice?rolls=abc"

   # Non-positive rolls — returns HTTP 500 with empty body
   curl "http://localhost:8080/rolldice?rolls=-1"

Telemetry output
~~~~~~~~~~~~~~~~

Span and metric data is printed to stdout (via the console exporters) even
without a running collector, so you can verify instrumentation locally.

Configuration
-------------

Telemetry behavior is defined in ``otel-config.yaml``.  You can edit this file
to add or remove exporters, change sampling strategies, or adjust processor
settings — no code changes required.

Environment variables
---------------------

+-----------------------------------+----------------------------------------------+-------------------------+
| Variable                          | Description                                  | Default                 |
+===================================+==============================================+=========================+
| ``OTEL_EXPORTER_OTLP_ENDPOINT``   | OTLP HTTP endpoint for the backend           | ``http://localhost:4318``|
+-----------------------------------+----------------------------------------------+-------------------------+
| ``OTEL_RESOURCE_ATTRIBUTES``      | Extra resource attributes (``key=value,...``)| *(none)*                |
+-----------------------------------+----------------------------------------------+-------------------------+
| ``APPLICATION_PORT``              | Listening port                               | ``8080``                |
+-----------------------------------+----------------------------------------------+-------------------------+

.. note::

   ``OTEL_SERVICE_NAME`` is set to ``rolldice`` in ``otel-config.yaml``.  To
   override it, edit the config file or add ``service.name`` to
   ``OTEL_RESOURCE_ATTRIBUTES``.

Run with an OTLP backend
------------------------

Start the `OpenTelemetry Collector <https://opentelemetry.io/docs/collector/>`_ or
another OTLP-compatible backend, then:

.. code-block:: bash

   OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 \
   uvicorn app.main:app --host 0.0.0.0 --port 8080

Docker
------

Build:

.. code-block:: bash

   docker build -t rolldice .

Run (without a collector — console output only):

.. code-block:: bash

   docker run -p 8080:8080 rolldice

Run (with a collector on the host):

.. code-block:: bash

   docker run -p 8080:8080 \
     -e OTEL_EXPORTER_OTLP_ENDPOINT=http://host.docker.internal:4318 \
     rolldice
