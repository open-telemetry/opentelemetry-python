# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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

        def handle(self, error: Exception, *args, **kwargs):

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

from pkg_resources import iter_entry_points

logger = getLogger(__name__)


class ErrorHandler(ABC):
    @abstractmethod
    def handle(self, error: Exception, *args, **kwargs):
        """
        Handle an exception
        """


class DefaultErrorHandler(ErrorHandler):
    """
    Default error handler

    This error handler just logs the exception using standard logging.
    """

    # pylint: disable=useless-return
    def handle(self, error: Exception, *args, **kwargs):

        logger.exception("Error handled by default error handler: ")
        return None


class GlobalErrorHandler:
    """
    Global error handler

    This is a singleton class that can be instantiated anywhere to get the
    global error handler. This object provides a handle method that receives
    an exception object that will be handled by the registered error handlers.
    """

    _instance = None

    def __new__(cls) -> "GlobalErrorHandler":
        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __enter__(self):
        pass

    # pylint: disable=no-self-use
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_value is not None:
            self.handle(exc_value)
            return True
        return None

    def handle(self, error: Exception):
        """
        Handle the error through the registered error handlers.
        """

        error_handling_result = {}

        for error_handler_entry_point in iter_entry_points(
            "opentelemetry_error_handler"
        ):

            error_handler_class = error_handler_entry_point.load()

            if issubclass(error_handler_class, error.__class__):

                try:

                    error_handling_result[
                        error_handler_class
                    ] = error_handler_class().handle(error)

                # pylint: disable=broad-except
                except Exception as error_handling_error:

                    logger.exception(
                        "Error while handling error " "by %s error handler",
                        error_handler_class.__name__,
                    )

                    error_handling_result[
                        error_handler_class
                    ] = error_handling_error

        if not error_handling_result:

            # pylint: disable=assignment-from-none
            error_handling_result[
                DefaultErrorHandler
            ] = DefaultErrorHandler().handle(error)

        return error_handling_result
