README
======

Overview
--------

This is a prototype to implement `error handling`_ in Python.

The user only calls API functions or methods, never SDK functions or methods.

Every SDK must implement every public function or method defined in the API
except for the SDK setting function.

A safety mechanism is applied to every API function or method (except for the
SDK setting function or method) and only to every API function or method.

This safety mechanism has 3 main components:

1. A predefined value to be returned in case of an exception being raised. This
   value is predefined and independently set for every function or method.
2. A `try` / `except` block that catches any exception raised when executing
   the function or method code.
3. A Python `warning`_ that is "raised" if an exception is raised in the code
   protected by the safety mechanism.

The API provides a function to set a specific SDK. This function is
intentionally not protected by the safety mechanism mentioned above because the
specification `mentions`_ this:

    The API or SDK may fail fast and cause the application to fail on
    initialization...

*Initialization* is understood as the process of setting the SDK.

When an API function or method is called without an SDK being set, a warning
will be raised and the predefined value of `None` will be returned.

After an SDK is set, calling an API function or method will call its
corresponding SDK function or method. Any exception raised by the SDK function
or method will be caught by the safety mechanism and the predefined value
returned instead.

The Python warning that is "raised" when an exception is raised in the SDK
function or method can be transformed into a full exception by running the
Python interpreter with the `-W error` option. This Python feature is used to
satisfy this `specification requirement`_.

How to run
----------

0. Create a virtual environment and activate it
1. Run ``pip install -e opentelemetry-api``
2. Run ``pip install -e opentelemetry-sdk``
3. Run ``python application.py``
4. Run ``python -W error application.py``

Noice how even failed operations (divisions by zero) don't crash the
application in step 3, but they do in step 4.


.. _error handling: https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/error-handling.md
.. _warning: https://docs.python.org/3/library/warnings.html
.. _specification requirement: https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/error-handling.md#configuring-error-handlers
.. _mentions: https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/error-handling.md#basic-error-handling-principles
