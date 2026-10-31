# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""
Global Error Handler

This module provides a global error handler and an interface that allows
error handlers to be registered with the global error handler via entry points.
A default error handler is also provided.

To use this feature, users can create an error handler that is registered
using the ``opentelemetry_error_handler`` entry point. A class is to be
registered in this entry point, this class must inherit from the
``opentelemetry.sdk.error_handler.ErrorHandler`` class and implement the
corresponding ``handle`` method. This method will receive the exception object
that is to be handled. The error handler class should also inherit from the
exception classes it wants to handle. For example, this would be an error
handler that handles ``ZeroDivisionError``:

.. code:: python

    from opentelemetry.sdk.error_handler import ErrorHandler
    from logging import getLogger

    logger = getLogger(__name__)


    class ErrorHandler0(ErrorHandler, ZeroDivisionError):

        def _handle(self, error: Exception, *args, **kwargs):

            logger.exception("ErrorHandler0 handling a ZeroDivisionError")

To use the global error handler, just instantiate it as a context manager where
you want exceptions to be handled:


.. code:: python

    from opentelemetry.sdk.error_handler import GlobalErrorHandler

    with GlobalErrorHandler():
        1 / 0

If the class of the exception raised in the scope of the ``GlobalErrorHandler``
object is not parent of any registered error handler, then the default error
handler will handle the exception. This default error handler will only log the
exception to standard logging, the exception won't be raised any further.
"""

from abc import ABC, abstractmethod
from logging import getLogger

from opentelemetry.util._importlib_metadata import entry_points

logger = getLogger(__name__)


class ErrorHandler(ABC):
    """Base class every registered error handler inherits from.

    A handler also inherits from each exception class it wants to handle, and
    ``GlobalErrorHandler`` selects it by testing that inheritance against the
    exception that was raised. A handler that inherits only from this class
    therefore handles nothing.
    """

    @abstractmethod
    def _handle(self, error: Exception, *args, **kwargs):
        """
        Handle an exception

        A handler is built with no arguments and this method is called once
        per matching handler. Returning normally counts as having handled the
        exception, which stops the default handler from also logging it.

        Args:
            error: The exception that was raised inside the
                ``GlobalErrorHandler`` block.
            *args: Accepted so that a handler can take extra positional
                arguments. ``GlobalErrorHandler`` passes none.
            **kwargs: Accepted so that a handler can take extra keyword
                arguments. ``GlobalErrorHandler`` passes none.
        """


class _DefaultErrorHandler(ErrorHandler):
    """
    Default error handler

    This error handler just logs the exception using standard logging.
    """

    # pylint: disable=useless-return
    def _handle(self, error: Exception, *args, **kwargs):
        """Log the exception and its traceback, then swallow it.

        The message is written at ``ERROR`` level to the logger of this
        module, so it reaches whatever handlers the application configured.
        The exception is not re-raised.

        Args:
            error: The exception that was raised. It is not formatted into
                the message; ``logger.exception`` takes the traceback from
                the exception being handled instead.
            *args: Ignored.
            **kwargs: Ignored.
        """
        logger.exception("Error handled by default error handler: ")


class GlobalErrorHandler:
    """
    Global error handler

    This is a singleton class that can be instantiated anywhere to get the
    global error handler. This object provides a handle method that receives
    an exception object that will be handled by the registered error handlers.
    """

    _instance = None

    def __new__(cls) -> "GlobalErrorHandler":
        """Return the one instance, creating it on the first call.

        Returns:
            The single instance, so that every ``with GlobalErrorHandler():``
            in the process shares one object. The class carries no state, so
            sharing it costs nothing and nesting two blocks is safe.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __enter__(self):
        """Enter the block, doing nothing.

        Returns:
            ``None``. There is nothing useful to bind with ``as``.
        """

    # pylint: disable=no-self-use
    def __exit__(self, exc_type, exc_value, traceback):
        """Dispatch an escaping exception to the registered handlers.

        Every entry point in the ``opentelemetry_error_handler`` group is
        loaded on each exception, and a handler class is selected when it is a
        subclass of the class of the raised exception, which is what the
        module docstring means by a handler inheriting from the exceptions it
        handles. A handler for a base class is therefore not selected for a
        derived exception. Several handlers can match one exception and all
        of them run. An exception raised by a handler is logged and the
        remaining handlers still run, but that handler does not count as
        having handled anything.

        When no handler matched, or every handler that matched raised, the
        default handler logs the exception.

        Args:
            exc_type: The class of the escaping exception, or ``None`` when
                the block finished normally. It is not used; the dispatch
                reads the class off ``exc_value``.
            exc_value: The escaping exception, or ``None`` when the block
                finished normally.
            traceback: The traceback of the escaping exception. It is not
                used.

        Returns:
            ``None`` when the block finished normally. ``True`` when an
            exception escaped, which suppresses it, so an exception raised
            inside the block never reaches the surrounding code.
        """
        if exc_value is None:
            return None

        plugin_handled = False

        error_handler_entry_points = entry_points(group="opentelemetry_error_handler")

        for error_handler_entry_point in error_handler_entry_points:
            error_handler_class = error_handler_entry_point.load()

            if issubclass(error_handler_class, exc_value.__class__):
                try:
                    error_handler_class()._handle(exc_value)
                    plugin_handled = True

                # pylint: disable=broad-exception-caught
                except Exception as error_handling_error:
                    logger.exception(
                        "%s error while handling error %s by error handler %s",
                        error_handling_error.__class__.__name__,
                        exc_value.__class__.__name__,
                        error_handler_class.__name__,
                    )

        if not plugin_handled:
            _DefaultErrorHandler()._handle(exc_value)

        return True
