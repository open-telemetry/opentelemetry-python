opentelemetry.context package
=============================

OpenTelemetry context values are immutable snapshots. Functions such as
``set_value`` and baggage helpers return a new ``Context`` object rather
than mutating the current one.

There are two common ways to use a context:

* Pass it explicitly to APIs that accept a ``context=...`` parameter.
* Attach it with ``context.attach`` so it becomes the current context
  for the current execution unit, then restore the previous current
  context with ``context.detach``.

Example:

.. code-block:: python

   from opentelemetry import context

   ctx = context.set_value("key", "value")

   print(context.get_current().get("key"))
   # None

   token = context.attach(ctx)
   try:
       print(context.get_current().get("key"))
       # value
   finally:
       context.detach(token)

This is the same model used by :mod:`opentelemetry.baggage`.

Submodules
----------

.. toctree::

   context.context

Module contents
---------------

.. automodule:: opentelemetry.context

