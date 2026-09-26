OpenTelemetry Semantic Conventions
==================================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-semantic-conventions.svg
   :target: https://pypi.org/project/opentelemetry-semantic-conventions/

This library contains generated code for the `OpenTelemetry Semantic Conventions`_.

Installation
------------

::

    pip install opentelemetry-semantic-conventions

Supported Semantic Conventions Version
--------------------------------------

This release of the package is generated from
`OpenTelemetry Semantic Conventions v1.44.0 <https://github.com/open-telemetry/semantic-conventions/tree/v1.44.0>`_.

The version of this package is independent of the semantic conventions version it
is generated from. Check this section, or ``opentelemetry.semconv.schemas.Schemas``,
to find out which semantic conventions version a given release supports.

Stability
---------

This package follows `Semantic Versioning <https://semver.org/>`_ for its
**public** modules only (i.e. portions of the Semantic Conventions which have
been marked as **stable**).

Stable modules
~~~~~~~~~~~~~~

The following modules contain only conventions marked **stable** upstream:

* ``opentelemetry.semconv.attributes.*``
* ``opentelemetry.semconv.metrics.*``
* ``opentelemetry.semconv.schemas``

Within the 1.x release line, these modules will not remove or rename any symbol.
Upgrading can still change them in the following ways:

* New attributes, metrics, enum members and schema URLs may be added in minor releases.
* An attribute or metric may be **deprecated** when the semantic conventions deprecate it.
  Deprecated symbols are documented as deprecated (enum classes are also marked with
  ``@deprecated``), but remain available.
* Documentation (docstrings) may change.

Incubating modules
~~~~~~~~~~~~~~~~~~

.. warning::

   Anything under ``opentelemetry.semconv._incubating`` is **not** covered by
   Semantic Versioning and is subject to breaking changes across **minor** (and patch)
   versions of this package.

``opentelemetry.semconv._incubating.attributes.*`` and
``opentelemetry.semconv._incubating.metrics.*`` contain every convention in the
semantic conventions registry, including those in development or experimental/deprecated
ones. These can be renamed, changed or removed upstream at any time
and this package will follow those changes without a major version bump.

.. important::

   Libraries that depend on anything under ``opentelemetry.semconv._incubating``
   **SHOULD** pin an exact version of this package, for example::

       dependencies = [
           "opentelemetry-semantic-conventions == 1.46.0",
       ]

   A version range such as ``~= 1.46`` or ``>= 1.46`` can break your library when a
   new minor version of this package is released.

The ``_incubating`` modules also contain copies of the stable conventions, marked as
deprecated in favor of the stable module. When a convention is available in a stable
module, import it from there.

Other caveats
~~~~~~~~~~~~~

* Not every semantic conventions namespace is generated. Namespaces specific to other
  languages or runtimes (e.g. ``jvm``, ``dotnet``, ``go`` and ``nodejs``) are
  excluded. See ``excluded_namespaces`` in the
  `weaver configuration <https://github.com/open-telemetry/opentelemetry-python/blob/main/scripts/semconv/templates/registry/weaver.yaml>`_.
  Excluded namespaces may be added in a future minor release.
* ``opentelemetry.semconv.trace`` and ``opentelemetry.semconv.resource`` are legacy
  modules and are deprecated. Use ``opentelemetry.semconv.attributes`` or
  ``opentelemetry.semconv._incubating.attributes`` instead.

Contributing
------------

This package is generated. See `DEVELOPMENT.md`_ for how to regenerate it and
the compatibility rules maintainers must follow.

References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
* `OpenTelemetry Semantic Conventions`_
* `Semantic Conventions repository <https://github.com/open-telemetry/semantic-conventions>`_
* `Semantic Conventions stability guarantees <https://opentelemetry.io/docs/specs/otel/versioning-and-stability/#semantic-conventions-stability>`_

.. _OpenTelemetry Semantic Conventions: https://opentelemetry.io/docs/specs/semconv/
.. _DEVELOPMENT.md: https://github.com/open-telemetry/opentelemetry-python/blob/main/opentelemetry-semantic-conventions/DEVELOPMENT.md
