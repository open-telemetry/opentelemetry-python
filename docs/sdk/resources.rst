opentelemetry.sdk.resources package
==========================================

Host resource detection
-----------------------

The host resource detector populates the attributes defined by the
`host resource semantic conventions
<https://opentelemetry.io/docs/specs/semconv/resource/host/>`_.

Enable the host resource detector by setting
:envvar:`OTEL_EXPERIMENTAL_RESOURCE_DETECTORS` before starting your application:

.. code-block:: sh

    export OTEL_EXPERIMENTAL_RESOURCE_DETECTORS=host

Resources created with :meth:`opentelemetry.sdk.resources.Resource.create`
will then include ``host.name``, ``host.arch``, and, when available, ``host.id``.
If you already configure other detectors, add ``host`` to the comma-separated
list.

The detector obtains ``host.id`` using the sources listed for a
`non-privileged machine id lookup
<https://opentelemetry.io/docs/specs/semconv/resource/host/#non-privileged-machine-id-lookup>`_:

* Linux: ``/etc/machine-id``, falling back to ``/var/lib/dbus/machine-id``.
* BSD: ``/etc/hostid``, falling back to ``/bin/kenv -q smbios.system.uuid``.
* macOS: ``IOPlatformUUID`` from ``/usr/sbin/ioreg -rd1 -c IOPlatformExpertDevice``.
* Windows: ``MachineGuid`` from
  ``HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Cryptography``, using the 64-bit registry
  view.

If the lookup fails or the operating system is unsupported, ``host.id`` is
omitted by default while ``host.name`` and ``host.arch`` are retained. You can
provide an explicit value through :envvar:`OTEL_RESOURCE_ATTRIBUTES`, for
example ``OTEL_RESOURCE_ATTRIBUTES=host.id=my-host-id``. With the detector order
shown above, this value takes precedence over the detected value.

API
---

.. automodule:: opentelemetry.sdk.resources
    :members:
    :undoc-members:
    :show-inheritance:
