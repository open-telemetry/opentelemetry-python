# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from logging import ERROR
from unittest import TestCase
from unittest.mock import Mock, patch

from opentelemetry.sdk.error_handler import (
    ErrorHandler,
    GlobalErrorHandler,
    logger,
)


class TestErrorHandler(TestCase):
    @patch("opentelemetry.sdk.error_handler.entry_points")
    def test_default_error_handler(self, mock_entry_points):
        with self.assertLogs(logger, ERROR):
            with GlobalErrorHandler():
                # pylint: disable=broad-exception-raised
                raise Exception("some exception")

    # pylint: disable=no-self-use
    @patch("opentelemetry.sdk.error_handler.entry_points")
    def test_plugin_error_handler(self, mock_entry_points):
        class ZeroDivisionErrorHandler(ErrorHandler, ZeroDivisionError):
            # pylint: disable=arguments-differ

            _handle = Mock()

        class AssertionErrorHandler(ErrorHandler, AssertionError):
            # pylint: disable=arguments-differ

            _handle = Mock()

        mock_entry_point_zero_division_error_handler = Mock()
        mock_entry_point_zero_division_error_handler.configure_mock(
            **{"load.return_value": ZeroDivisionErrorHandler}
        )
        mock_entry_point_assertion_error_handler = Mock()
        mock_entry_point_assertion_error_handler.configure_mock(
            **{"load.return_value": AssertionErrorHandler}
        )

        mock_entry_points.configure_mock(
            **{
                "return_value": [
                    mock_entry_point_zero_division_error_handler,
                    mock_entry_point_assertion_error_handler,
                ]
            }
        )

        error = ZeroDivisionError()

        with GlobalErrorHandler():
            raise error

        # pylint: disable=protected-access
        ZeroDivisionErrorHandler._handle.assert_called_with(error)

        error = AssertionError()

        with GlobalErrorHandler():
            raise error

        AssertionErrorHandler._handle.assert_called_with(error)

    @patch("opentelemetry.sdk.error_handler.entry_points")
    def test_error_in_handler(self, mock_entry_points):
        class ErrorErrorHandler(ErrorHandler, ZeroDivisionError):
            # pylint: disable=arguments-differ

            def _handle(self, error: Exception):
                assert False

        mock_entry_point_error_error_handler = Mock()
        mock_entry_point_error_error_handler.configure_mock(
            **{"load.return_value": ErrorErrorHandler}
        )

        mock_entry_points.configure_mock(
            **{"return_value": [mock_entry_point_error_error_handler]}
        )

        error = ZeroDivisionError()

        with self.assertLogs(logger, ERROR):
            with GlobalErrorHandler():
                raise error

    # pylint: disable=no-self-use
    @patch("opentelemetry.sdk.error_handler.entry_points")
    def test_plugin_error_handler_context_manager(self, mock_entry_points):
        mock_error_handler_instance = Mock()

        class MockErrorHandlerClass(IndexError):
            def __new__(cls):
                return mock_error_handler_instance

        mock_entry_point_error_handler = Mock()
        mock_entry_point_error_handler.configure_mock(
            **{"load.return_value": MockErrorHandlerClass}
        )

        mock_entry_points.configure_mock(
            **{"return_value": [mock_entry_point_error_handler]}
        )

        error = IndexError()

        with GlobalErrorHandler():
            raise error

        with GlobalErrorHandler():
            pass

        # pylint: disable=protected-access
        mock_error_handler_instance._handle.assert_called_once_with(error)
