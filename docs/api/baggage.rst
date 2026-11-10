opentelemetry.baggage package
========================================

The baggage API stores name/value pairs in an OpenTelemetry
``Context``. The helper functions in :mod:`opentelemetry.baggage`
return updated ``Context`` values. They do not mutate or attach the
current context automatically.

This distinction matters when reading baggage:

* ``baggage.get_all()`` reads from the current context.
* ``baggage.get_all(context=ctx)`` reads from the explicit context.
* ``baggage.set_baggage(...)`` returns a context containing the new
  baggage entry.

For example:

.. code-block:: python

   from opentelemetry import baggage

   ctx = baggage.set_baggage("tenant", "acme")

   print(baggage.get_all())
   # {}

   print(dict(baggage.get_all(context=ctx)))
   # {'tenant': 'acme'}

To make the returned context current for the current execution unit,
attach it and later detach it with the token returned by
``context.attach``:

.. code-block:: python

   from opentelemetry import baggage, context

   ctx = baggage.set_baggage("tenant", "acme")
   token = context.attach(ctx)
   try:
       print(dict(baggage.get_all()))
       # {'tenant': 'acme'}
   finally:
       context.detach(token)

Always pair ``context.attach`` with ``context.detach``. Dropping the
token can leak baggage into later work on the same execution unit.

Passing ``context=...`` to another API is also different from attaching
that context. For example, ``tracer.start_as_current_span(...,
context=ctx)`` uses ``ctx`` to choose the parent span, but it does not
make ``ctx`` current for later calls to ``baggage.get_all()``. Attach
the context first when the current baggage should be visible inside the
span scope:

.. code-block:: python

   from opentelemetry import baggage, context, trace

   tracer = trace.get_tracer(__name__)
   ctx = baggage.set_baggage("tenant", "acme")

   token = context.attach(ctx)
   try:
       with tracer.start_as_current_span("work"):
           print(dict(baggage.get_all()))
           # {'tenant': 'acme'}
   finally:
       context.detach(token)

Subpackages
-----------

.. toctree::

   baggage.propagation

Module contents
---------------

.. automodule:: opentelemetry.baggage
