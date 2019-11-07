
Nested callbacks example.
=========================

This example shows a ``Span`` for a top-level operation, and how it can be passed down on a list of nested callbacks (always one at a time), have it as the active one for each of them, and finished **only** when the last one executes. For Python, we have decided to do it in a **fire-and-forget** fashion.

Implementation details:


* For ```asyncio`` and ``threading``\ , the ``Span`` is manually passed down the call chain, activating it in each corotuine/task.
* For ``tornado``\ , the active ``Span`` is not passed nor activated down the chain as the  ``Context`` automatically propagates it.

``threading`` implementation:

.. code-block:: python

       def submit(self):
           span = self.tracer.scope_manager.active.span

           def task1():
               with self.tracer.scope_manager.activate(span, False):
                   span.set_tag("key1', '1")

                   def task2():
                       with self.tracer.scope_manager.activate(span, False):
                           span.set_tag("key2', '2")
                           ...

``tornado`` implementation:

.. code-block:: python

       @gen.coroutine
       def submit(self):
           span = self.tracer.scope_manager.active.span

           @gen.coroutine
           def task1():
               self.assertEqual(span, self.tracer.scope_manager.active.span)
               span.set_tag("key1', '1")

               @gen.coroutine
               def task2():
                   self.assertEqual(span,
                                    self.tracer.scope_manager.active.span)
                   span.set_tag("key2', '2")
