Global Error Handler
====================

Overview
--------

This example shows how to use the global error handler.


Preparation
-----------

This example will be executed in a separate virtual environment:

.. code:: sh

    $ mkdir global_error_handler
    $ virtualenv global_error_handler
    $ source global_error_handler/bin/activate

Installation
------------

Here we install first ``opentelemetry-sdk``, the only dependency. Afterwards, 2
error handlers are installed: ``error_handler_0``  will handle
``ZeroDivisionError`` exceptions, ``error_handler_1`` will handle
``IndexError`` and ``KeyError`` exceptions.

.. code:: sh

    $ pip install opentelemetry-sdk
    $ git clone https://github.com/open-telemetry/opentelemetry-python.git
    $ pip install -e opentelemetry-python/docs/examples/error_handler/error_handler_0
    $ pip install -e opentelemetry-python/docs/examples/error_handler/error_handler_1

Execution
---------

An example is provided in the
``opentelemetry-python/docs/examples/error_handler/example.py``.

You can just run it, you should get output similar to this one:

.. code:: pytb

    ErrorHandler0 handling a ZeroDivisionError
    Traceback (most recent call last):
      File "test.py", line 5, in <module>
        1 / 0
    ZeroDivisionError: division by zero

    ErrorHandler1 handling an IndexError
    Traceback (most recent call last):
      File "test.py", line 11, in <module>
        [1][2]
    IndexError: list index out of range

    ErrorHandler1 handling a KeyError
    Traceback (most recent call last):
      File "test.py", line 17, in <module>
        {1: 2}[2]
    KeyError: 2

    Error handled by default error handler: 
    Traceback (most recent call last):
      File "test.py", line 23, in <module>
        assert False
    AssertionError

    No error raised

The ``opentelemetry-sdk.error_handler`` module includes documentation that
explains how this works. We recommend you read it also, here is just a small
summary.

In ``example.py`` we use ``GlobalErrorHandler`` as a context manager in several
places, for example:


.. code:: python

    with GlobalErrorHandler():
        {1: 2}[2]

Running that code will raise a ``KeyError`` exception.
``GlobalErrorHandler`` will "capture" that exception and pass it down to the
registered error handlers. If there is one that handles ``KeyError`` exceptions
then it will handle it. That can be seen in the result of the execution of
``example.py``:

.. code::

    ErrorHandler1 handling a KeyError
    Traceback (most recent call last):
      File "test.py", line 17, in <module>
        {1: 2}[2]
    KeyError: 2

There is no registered error handler that can handle ``AssertionError``
exceptions so this kind of errors are handled by the default error handler
which just logs the exception to standard logging, as seen here:

.. code::

    Error handled by default error handler: 
    Traceback (most recent call last):
      File "test.py", line 23, in <module>
        assert False
    AssertionError

When no exception is raised, the code inside the scope of
``GlobalErrorHandler`` is exectued normally:

.. code::

    No error raised

Users can create Python packages that provide their own custom error handlers
and install them in their virtual environments before running their code which
instantiates ``GlobalErrorHandler`` context managers. ``error_handler_0`` and
``error_handler_1`` can be used as examples to create these custom error
handlers.

In order for the error handlers to be registered, they need to create a class
that inherits from ``opentelemetry.sdk.error_handler.ErrorHandler`` and at
least one ``Exception``-type class. For example, this is an error handler that
handles ``ZeroDivisionError`` exceptions:

.. code:: python

    from opentelemetry.sdk.error_handler import ErrorHandler
    from logging import getLogger

    logger = getLogger(__name__)


    class ErrorHandler0(ErrorHandler, ZeroDivisionError):

        def handle(self, error: Exception, *args, **kwargs):

            logger.exception("ErrorHandler0 handling a ZeroDivisionError")

To register this error handler, use the ``opentelemetry_error_handler`` entry
point in the setup of the error handler package:

.. code::

    [options.entry_points]
    opentelemetry_error_handler =
        error_handler_0 = error_handler_0:ErrorHandler0

This entry point should point to the error handler class, ``ErrorHandler0`` in
this case.
