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

from abc import ABC, abstractmethod
from pkg_resources import iter_entry_points
from logging import getLogger

logger = getLogger(__name__)


class ErrorHandler(ABC):

    @abstractmethod
    def handle(error: Exception, *args, **kwargs):
        """
        Handle an exception
        """


class DefaultErrorHandler(ErrorHandler):
    """
    Default error handler

    This error handler just logs the exception using standard logging.
    """

    def handle(error: Exception, *args, **kwargs):

        logger.exception("Error handled by default error handler: ")


class GlobalErrorHandler:

    def handle(error: Exception):
        """
        Handle the error through the registered error handlers.
        """

        handling_result = {}

        for error_handler_class in iter_entry_points(
            "opentelemetry_error_handler"
        ):

            if issubclass(error_handler_class, error):

                handling_result[
                    error_handler_class
                ] = error_handler_class().handle(error)

        return handling_result
