OpenTelemetry Process Context
==============================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-process-context.svg
   :target: https://pypi.org/project/opentelemetry-process-context/

This library implements the `OpenTelemetry Process Context`_ specification (OTEP 4719).
It serializes the process's OTel ``Resource`` attributes into a protobuf payload and
publishes them into a named memory mapped region called ``OTEL_CTX``, making the
process discoverable by out-of-process readers such as the
`OpenTelemetry eBPF Profiler`_ via ``/proc/<pid>/maps`` and ``/proc/<pid>/mem`` on
Linux without any in-process integration or network communication.

.. _OpenTelemetry Process Context: https://github.com/open-telemetry/opentelemetry-specification/blob/main/oteps/profiles/4719-process-ctx.md
.. _OpenTelemetry eBPF Profiler: https://github.com/open-telemetry/opentelemetry-ebpf-profiler

Installation
------------

::

    pip install opentelemetry-process-context

Platform Requirements
---------------------

This package targets Linux. On Linux the mapping is created via ``memfd`` so it
appears as a named entry (``/memfd:OTEL_CTX``) in ``/proc/<pid>/maps``, and
``MADV_DONTFORK`` prevents child processes from inheriting it. A fallback to an
anonymous ``mmap`` is provided for other Unix-like systems, non-Unix and 32-bit
platforms raise ``RuntimeError``.

Usage
-----

Call ``publish_context`` with the same ``Resource`` used to configure your
OpenTelemetry SDK provider. The mapping stays live for the lifetime of the process.
Call ``unpublish_context`` on shutdown to remove it explicitly.

.. code-block:: python

    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.process_context import publish_context, unpublish_context

    resource = Resource(attributes={
        "service.name": "my-service",
        "service.version": "1.0.0",
    })

    provider = TracerProvider(resource=resource)
    # register provider with trace / metrics / logs APIs ...

    publish_context(resource)

    # On shutdown (optional):
    unpublish_context()

References
----------

* `OpenTelemetry Process Context specification (OTEP 4719) <https://github.com/open-telemetry/opentelemetry-specification/blob/main/oteps/profiles/4719-process-ctx.md>`_
* `OpenTelemetry eBPF Profiler <https://github.com/open-telemetry/opentelemetry-ebpf-profiler>`_
* `OpenTelemetry <https://opentelemetry.io/>`_
