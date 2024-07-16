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

import threading
import time
import unittest
from itertools import repeat
from logging import WARNING
from typing import Type
from unittest.mock import ANY, Mock, patch

from opentelemetry.exporter.otlp.proto.common.exporter import (
    RetryableExportError,
    RetryingExporter,
)
from opentelemetry.exporter.otlp.proto.common.exporter import (
    logger as exporter_logger,
)

result_type: Type = Mock()


class TestRetryableExporter(unittest.TestCase):
    def test_export_no_retry(self):
        export_func = Mock()
        exporter = RetryingExporter(export_func, result_type, timeout_sec=10.0)
        with self.subTest("Export success"):
            export_func.reset_mock()
            export_func.configure_mock(return_value=result_type.SUCCESS)
            with self.assertRaises(AssertionError):
                with self.assertLogs(level=WARNING):
                    result = exporter.export_with_retry("payload")
            self.assertIs(result, result_type.SUCCESS)
            export_func.assert_called_once_with(
                "payload", ANY
            )  # Timeout checked in the following line
            self.assertAlmostEqual(
                export_func.call_args_list[0][0][1], 10.0, places=4
            )

        with self.subTest("Export Fail"):
            export_func.reset_mock()
            export_func.configure_mock(return_value=result_type.FAILURE)
            with self.assertRaises(AssertionError):
                with self.assertLogs(exporter_logger, level=WARNING):
                    result = exporter.export_with_retry("payload")
            self.assertIs(result, result_type.FAILURE)
            export_func.assert_called_once_with(
                "payload", ANY
            )  # Timeout checked in the following line
            self.assertAlmostEqual(
                export_func.call_args_list[0][0][1], 10.0, places=4
            )

    @patch(
        "opentelemetry.exporter.otlp.proto.common.exporter._create_exp_backoff_generator",
        return_value=repeat(0),
    )
    def test_export_retry(self, mock_backoff):
        """
        Test we retry until success/failure.
        """
        side_effect = [
            RetryableExportError(None),
            RetryableExportError(None),
            result_type.SUCCESS,
        ]
        export_func = Mock(side_effect=side_effect)
        exporter = RetryingExporter(export_func, result_type, timeout_sec=0.1)

        with self.subTest("Retry until success"):
            with patch.object(
                exporter._shutdown, "wait"  # pylint: disable=protected-access
            ) as wait_mock, self.assertLogs(level=WARNING):
                result = exporter.export_with_retry("")
            self.assertEqual(wait_mock.call_count, len(side_effect) - 1)
            self.assertEqual(export_func.call_count, len(side_effect))
            self.assertIs(result, result_type.SUCCESS)

        with self.subTest("Retry until failure"):
            export_func.reset_mock()
            side_effect.insert(0, RetryableExportError(None))
            side_effect[-1] = result_type.FAILURE
            export_func.configure_mock(side_effect=side_effect)
            with self.assertLogs(level=WARNING):
                result = exporter.export_with_retry("")
            self.assertEqual(export_func.call_count, len(side_effect))
            self.assertIs(result, result_type.FAILURE)

    def test_export_uses_arg_timout_when_given(self) -> None:
        export_func = Mock(side_effect=RetryableExportError(None))
        exporter = RetryingExporter(export_func, result_type, timeout_sec=2)
        with self.assertLogs(level=WARNING):
            start = time.time()
            exporter.export_with_retry("payload", 0.1)
            duration = time.time() - start
        self.assertAlmostEqual(duration, 0.1, places=1)

    @patch(
        "opentelemetry.exporter.otlp.proto.common.exporter._create_exp_backoff_generator",
        return_value=repeat(0.25),
    )
    def test_export_uses_retry_delay(self, mock_backoff):
        """
        Test we retry using the delay specified in the RPC error as a lower bound.
        """
        side_effects = [
            RetryableExportError(0.0),
            RetryableExportError(0.25),
            RetryableExportError(0.75),
            RetryableExportError(1.0),
            result_type.SUCCESS,
        ]
        exporter = RetryingExporter(
            Mock(side_effect=side_effects), result_type, timeout_sec=10.0
        )

        with patch.object(
            exporter._shutdown, "wait"  # pylint: disable=protected-access
        ) as wait_mock, self.assertLogs(level=WARNING):
            result = exporter.export_with_retry("payload")
        self.assertIs(result, result_type.SUCCESS)
        self.assertEqual(wait_mock.call_count, len(side_effects) - 1)
        self.assertEqual(wait_mock.call_args_list[1].args, (0.25,))
        self.assertEqual(wait_mock.call_args_list[2].args, (0.75,))
        self.assertEqual(wait_mock.call_args_list[3].args, (1.00,))

    @patch(
        "opentelemetry.exporter.otlp.proto.common.exporter._create_exp_backoff_generator",
        return_value=repeat(0.1),
    )
    def test_retry_delay_exceeds_timeout(self, mock_backoff):
        """
        Test we timeout if we can't respect retry_delay.
        """
        side_effects = [
            RetryableExportError(0.25),
            RetryableExportError(1.0),  # should timeout here
            result_type.SUCCESS,
        ]

        mock_export_func = Mock(side_effect=side_effects)
        exporter = RetryingExporter(
            mock_export_func,
            result_type,
            timeout_sec=0.5,
        )

        with self.assertLogs(level=WARNING):
            self.assertEqual(
                exporter.export_with_retry("payload"), result_type.FAILURE
            )
        self.assertEqual(mock_export_func.call_count, 2)

    def test_shutdown(self):
        """Test we refuse to export if shut down."""
        mock_export_func = Mock(return_value=result_type.SUCCESS)
        exporter = RetryingExporter(
            mock_export_func,
            result_type,
            timeout_sec=10.0,
        )

        self.assertEqual(
            exporter.export_with_retry("payload"), result_type.SUCCESS
        )
        mock_export_func.assert_called_once()
        exporter.shutdown()
        with self.assertLogs(level=WARNING) as warning:
            self.assertEqual(
                exporter.export_with_retry("payload"), result_type.FAILURE
            )
        self.assertEqual(
            warning.records[0].message,
            "Exporter already shutdown, ignoring batch",
        )
        mock_export_func.assert_called_once()

    @patch(
        "opentelemetry.exporter.otlp.proto.common.exporter._create_exp_backoff_generator",
        return_value=repeat(0.01),
    )
    def test_shutdown_wait_last_export(self, mock_backoff):
        """Test that shutdown waits for ongoing export to complete."""

        timeout_sec = 0.05

        class ExportFunc:
            is_exporting = threading.Event()
            ready_to_continue = threading.Event()
            side_effect = [
                RetryableExportError(None),
                RetryableExportError(None),
                result_type.SUCCESS,
            ]
            mock_export_func = Mock(side_effect=side_effect)

            def __call__(self, *args, **kwargs):
                self.is_exporting.set()
                self.ready_to_continue.wait()
                return self.mock_export_func(*args, **kwargs)

        export_func = ExportFunc()

        exporter = RetryingExporter(
            export_func, result_type, timeout_sec=timeout_sec
        )

        class ExportWrap:
            def __init__(self) -> None:
                self.result = None

            def __call__(self, *args, **kwargs):
                self.result = exporter.export_with_retry("payload")
                return self.result

        export_wrapped = ExportWrap()

        export_thread = threading.Thread(
            name="export_thread", target=export_wrapped
        )
        with self.assertLogs(level=WARNING):
            try:
                # Simulate shutdown occurring during retry process
                # Intended execution flow
                #
                #   main thread:
                #       - start export_thread
                #       - wait for is_exporting
                #   export_thread:
                #       - call export_func
                #       - set is_exporting
                #       - wait for ready_to_continue
                #   main thread:
                #       - start shutdown thread
                #       - sleep to yield to shutdown thread
                #   shutdown_thread:
                #       - block at acquiring lock held by export_thread
                #       - shutdown is now pending timeout/export completion
                #   main thread:
                #       - set ready_to_continue
                #       - join all threads
                export_thread.start()
                export_func.is_exporting.wait()
                start_time = time.time()
                shutdown_thread = threading.Thread(
                    name="shutdown_thread", target=exporter.shutdown
                )
                shutdown_thread.start()
                export_func.ready_to_continue.set()
            finally:
                export_thread.join()
                shutdown_thread.join()

        duration = time.time() - start_time
        self.assertLessEqual(duration, timeout_sec)
        # pylint: disable=protected-access
        self.assertTrue(exporter._shutdown)
        self.assertIs(export_wrapped.result, result_type.SUCCESS)

    def test_shutdown_timeout_cancels_export_retries(self):
        """Test that shutdown timing out cancels ongoing retries."""

        class ExportFunc:
            is_exporting = threading.Event()
            ready_to_continue = threading.Event()
            mock_export_func = Mock(side_effect=RetryableExportError(None))

            def __call__(self, *args, **kwargs):
                self.is_exporting.set()
                self.ready_to_continue.wait()
                return self.mock_export_func(*args, **kwargs)

        export_func = ExportFunc()

        exporter = RetryingExporter(export_func, result_type, timeout_sec=30.0)

        class ExportWrap:
            def __init__(self) -> None:
                self.result = None

            def __call__(self, *args, **kwargs):
                self.result = exporter.export_with_retry("payload")
                return self.result

        export_wrapped = ExportWrap()

        shutdown_timeout = 0.02

        export_thread = threading.Thread(target=export_wrapped)
        with self.assertLogs(level=WARNING) as warning:
            try:
                export_thread.start()
                export_func.is_exporting.wait()
                start_time = time.time()
                shutdown_thread = threading.Thread(
                    target=exporter.shutdown, args=[shutdown_timeout * 1e3]
                )
                shutdown_thread.start()
                export_func.ready_to_continue.set()
            finally:
                export_thread.join()
                shutdown_thread.join()
        duration = time.time() - start_time
        self.assertAlmostEqual(duration, shutdown_timeout, places=1)
        # pylint: disable=protected-access
        self.assertTrue(exporter._shutdown)
        self.assertIs(export_wrapped.result, result_type.FAILURE)
        print(warning.records)
        self.assertEqual(warning.records[0].message, "Retrying in 1.00s")
        self.assertEqual(
            warning.records[-1].message,
            "Export cancelled due to shutdown timing out",
        )
