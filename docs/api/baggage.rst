opentelemetry.baggage package
========================================

The baggage API stores name/value pairs inside an OpenTelemetry
``Context``. The helper functions in :mod:`opentelemetry.baggage`
return updated context objects; they do not mutate the current context
in place.

This distinction matters when reading baggage with
``baggage.get_all()``:

* ``baggage.get_all()`` reads from the current context.
* ``baggage.get_all(context=ctx)`` reads from the explicit context you
  pass in.
* ``baggage.set_baggage(...)`` returns a new context containing the
  baggage entry, but that returned context is not made current unless
  you explicitly attach it.

Example:

.. code-block:: python

   from opentelemetry import baggage, context

   ctx = baggage.set_baggage("foo", "bar")

   print(baggage.get_all())
   # {}

   print(baggage.get_all(context=ctx))
   # {'foo': 'bar'}

To make a context returned by ``set_baggage`` become the current
context, attach it and later detach it with the value that ``attach``
returns:

.. code-block:: python

   from opentelemetry import baggage, context

   ctx = baggage.set_baggage("foo", "bar")
   token = context.attach(ctx)
   try:
       print(baggage.get_all())
       # {'foo': 'bar'}
   finally:
       context.detach(token)

Always pair ``context.attach`` with ``context.detach``. Dropping the
token can leak baggage into later work on the same execution unit.

Passing ``context=...`` to another API is also different from attaching
that context. For example, ``tracer.start_as_current_span(...,
context=ctx)`` uses ``ctx`` as the parent span context, but does not by
itself make ``ctx`` the current execution context for subsequent calls
to ``baggage.get_all()``. If you want both behaviors, attach the context
before entering the span scope.

Subpackages
-----------

.. toctree::

   baggage.propagation

Module contents
---------------

.. automodule:: opentelemetry.baggage
