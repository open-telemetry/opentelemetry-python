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

from unittest import TestCase
from logging import ERROR, disable, NOTSET
from unittest.mock import patch, Mock

from opentelemetry.sdk.error_handler import (
    DefaultErrorHandler, logger, GlobalErrorHandler, ErrorHandler
)


class TestErrorHandler(TestCase):

    def test_default_error_handler(self):

        try:
            raise Exception("some exception")
        except Exception as error:
            with self.assertLogs(logger, ERROR):
                DefaultErrorHandler().handle(error)

        try:
            raise Exception("some exception")
        except Exception as error:
            with self.assertLogs(logger, ERROR):
                error_handling_result = GlobalErrorHandler().handle(error)

        self.assertIsNone(error_handling_result[DefaultErrorHandler])

    @patch("opentelemetry.sdk.error_handler.iter_entry_points")
    def test_plugin_error_handler(self, mock_iter_entry_points):

        class ZeroDivisionErrorHandler(ErrorHandler, ZeroDivisionError):

            def handle(self, error: Exception):
                return 0

        class AssertionErrorHandler(ErrorHandler, AssertionError):

            def handle(self, error: Exception):
                return 1

        mock_iter_entry_points.configure_mock(
            **{
                "return_value": [
                    ZeroDivisionErrorHandler, AssertionErrorHandler
                ]
            }
        )

        try:
            1 / 0
        except Exception as error:
            error_handling_result = GlobalErrorHandler().handle(error)

        self.assertEqual(error_handling_result, {ZeroDivisionErrorHandler: 0})

        try:
            assert False
        except Exception as error:
            error_handling_result = GlobalErrorHandler().handle(error)

        self.assertEqual(error_handling_result, {AssertionErrorHandler: 1})

        try:
            {}[1]
        except Exception as error:
            disable(ERROR)
            error_handling_result = GlobalErrorHandler().handle(error)
            disable(NOTSET)

        self.assertEqual(error_handling_result, {DefaultErrorHandler: None})

    @patch("opentelemetry.sdk.error_handler.iter_entry_points")
    def test_plugin_error_handler_context_manager(
        self, mock_iter_entry_points
    ):

        mock_error_handler_instance = Mock()

        class MockErrorHandlerClass(IndexError):

            def __new__(cls):
                return mock_error_handler_instance

        mock_iter_entry_points.configure_mock(
            **{"return_value": [MockErrorHandlerClass]}
        )

        error = IndexError()

        with GlobalErrorHandler():
            raise error

        with GlobalErrorHandler():
            pass

        mock_error_handler_instance.handle.assert_called_once_with(error)
