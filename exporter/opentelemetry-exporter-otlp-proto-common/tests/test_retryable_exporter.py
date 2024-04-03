import threading
import time
import unittest
from itertools import repeat
from logging import WARNING
from typing import Type
from unittest.mock import ANY, Mock, patch

from opentelemetry.exporter.otlp.proto.common.exporter import (
    _DEFAULT_EXPORT_TIMEOUT_S,
    RetryableExportError,
    RetryingExporter,
)
from opentelemetry.exporter.otlp.proto.common.exporter import (
    logger as exporter_logger,
)
from opentelemetry.sdk.environment_variables import OTEL_EXPORTER_OTLP_TIMEOUT

result_type: Type = Mock()


class TestRetryableExporter(unittest.TestCase):
    def test_export_no_retry(self):
        export_func = Mock()
        exporter = RetryingExporter(export_func, result_type)
        with self.subTest("Export success"):
            export_func.reset_mock()
            export_func.configure_mock(return_value=result_type.SUCCESS)
            pos_arg = Mock()
            with self.assertRaises(AssertionError):
                with self.assertLogs(level=WARNING):
                    result = exporter.export_with_retry(
                        _DEFAULT_EXPORT_TIMEOUT_S, pos_arg, foo="bar"
                    )
            self.assertIs(result, result_type.SUCCESS)
            export_func.assert_called_once_with(ANY, pos_arg, foo="bar")

        with self.subTest("Export Fail"):
            export_func.reset_mock()
            export_func.configure_mock(return_value=result_type.FAILURE)
            pos_arg = Mock()
            with self.assertRaises(AssertionError):
                with self.assertLogs(exporter_logger, level=WARNING):
                    result = exporter.export_with_retry(
                        _DEFAULT_EXPORT_TIMEOUT_S, pos_arg, foo="bar"
                    )
            self.assertIs(result, result_type.FAILURE)
            export_func.assert_called_once_with(ANY, pos_arg, foo="bar")

    @patch(
        "opentelemetry.exporter.otlp.proto.common.exporter._create_exp_backoff_with_jitter_generator",
        return_value=repeat(0),
    )
    def test_export_retry(self, mock_backoff):
        """
        Test we retry until success/failure.
        """
        side_effect = [
            RetryableExportError,
            RetryableExportError,
            result_type.SUCCESS,
        ]
        export_func = Mock(side_effect=side_effect)
        exporter = RetryingExporter(export_func, result_type)

        with self.subTest("Retry until success"):
            with self.assertLogs(level=WARNING):
                result = exporter.export_with_retry(10)
            self.assertEqual(export_func.call_count, len(side_effect))
            self.assertIs(result, result_type.SUCCESS)

        with self.subTest("Retry until failure"):
            export_func.reset_mock()
            side_effect.insert(0, RetryableExportError)
            side_effect[-1] = result_type.FAILURE
            export_func.configure_mock(side_effect=side_effect)
            with self.assertLogs(level=WARNING):
                result = exporter.export_with_retry(10)
            self.assertEqual(export_func.call_count, len(side_effect))
            self.assertIs(result, result_type.FAILURE)

    def test_export_uses_smallest_timeout(self):
        """
        Test that the exporter uses the smallest of attribute, argument,
        environment variable as timeout.
        """

        def patch_and_time(attrib_timeout, environ_timeout, arg_timeout):
            export_func = Mock(side_effect=RetryableExportError())
            with patch.dict(
                "os.environ",
                {OTEL_EXPORTER_OTLP_TIMEOUT: str(environ_timeout)},
            ):
                start = time.time()
                exporter = RetryingExporter(
                    export_func, result_type, timeout_s=attrib_timeout
                )
                with self.assertLogs(level=WARNING):
                    exporter.export_with_retry(arg_timeout)
            duration = time.time() - start
            self.assertAlmostEqual(
                duration,
                min(attrib_timeout, environ_timeout, arg_timeout),
                places=1,
            )

        patch_and_time(0.5, 10, 10)
        patch_and_time(10, 0.5, 10)
        patch_and_time(10, 10, 0.5)

    def test_explicit_environ_timeout_beats_default(self):
        """Ensure a specific timeout in environment can be higher than default."""
        with patch.dict(
            "os.environ",
            {OTEL_EXPORTER_OTLP_TIMEOUT: str(2 * _DEFAULT_EXPORT_TIMEOUT_S)},
        ):
            self.assertEqual(
                # pylint: disable=protected-access
                RetryingExporter(Mock(), result_type)._timeout_s,
                2 * _DEFAULT_EXPORT_TIMEOUT_S,
            )

    @patch(
        (
            "opentelemetry.exporter.otlp.proto.common.exporter"
            "._create_exp_backoff_with_jitter_generator"
        ),
        return_value=repeat(0.25),
    )
    def test_export_uses_retry_delay(self, mock_backoff):
        """
        Test we retry using the delay specified in the RPC error as a lower bound.
        """
        side_effects = [
            RetryableExportError(0),
            RetryableExportError(0.25),
            RetryableExportError(0.75),
            RetryableExportError(1),
            result_type.SUCCESS,
        ]
        exporter = RetryingExporter(
            Mock(side_effect=side_effects), result_type
        )

        # pylint: disable=protected-access
        with patch.object(exporter._shutdown_event, "wait") as wait_mock:
            with self.assertLogs(level=WARNING):
                result = exporter.export_with_retry(timeout_s=10, foo="bar")
        self.assertIs(result, result_type.SUCCESS)
        self.assertEqual(wait_mock.call_count, len(side_effects) - 1)
        self.assertEqual(wait_mock.call_args_list[0].args, (0.25,))
        self.assertEqual(wait_mock.call_args_list[1].args, (0.25,))
        self.assertEqual(wait_mock.call_args_list[2].args, (0.75,))
        self.assertEqual(wait_mock.call_args_list[3].args, (1.00,))

    @patch(
        (
            "opentelemetry.exporter.otlp.proto.common.exporter"
            "._create_exp_backoff_with_jitter_generator"
        ),
        return_value=repeat(0.1),
    )
    def test_retry_delay_exceeds_timeout(self, mock_backoff):
        """
        Test we timeout if we can't respect retry_delay.
        """
        side_effects = [
            RetryableExportError(0.25),
            RetryableExportError(1),  # should timeout here
            result_type.SUCCESS,
        ]

        mock_export_func = Mock(side_effect=side_effects)
        exporter = RetryingExporter(
            mock_export_func,
            result_type,
        )

        with self.assertLogs(level=WARNING):
            self.assertEqual(
                exporter.export_with_retry(0.5), result_type.FAILURE
            )
        self.assertEqual(mock_export_func.call_count, 2)

    def test_shutdown(self):
        """Test we refuse to export if shut down."""
        mock_export_func = Mock(return_value=result_type.SUCCESS)
        exporter = RetryingExporter(
            mock_export_func,
            result_type,
        )

        self.assertEqual(exporter.export_with_retry(10), result_type.SUCCESS)
        mock_export_func.assert_called_once()
        exporter.shutdown()
        with self.assertLogs(level=WARNING) as warning:
            self.assertEqual(
                exporter.export_with_retry(10), result_type.FAILURE
            )
        self.assertEqual(
            warning.records[0].message,
            "Exporter already shutdown, ignoring batch",
        )
        mock_export_func.assert_called_once()

    def test_shutdown_wait_last_export(self):
        """Test that shutdown waits for ongoing export to complete."""

        timeout_s = 10

        class ExportFunc:
            is_exporting = threading.Event()
            ready_to_continue = threading.Event()
            side_effect = [
                RetryableExportError(),
                RetryableExportError(),
                result_type.SUCCESS,
            ]
            mock_export_func = Mock(side_effect=side_effect)

            def __call__(self, *args, **kwargs):
                self.is_exporting.set()
                self.ready_to_continue.wait()
                return self.mock_export_func(*args, **kwargs)

        export_func = ExportFunc()

        exporter = RetryingExporter(
            export_func, result_type, timeout_s=timeout_s
        )

        class ExportWrap:
            def __init__(self) -> None:
                self.result = None

            def __call__(self, *args, **kwargs):
                self.result = exporter.export_with_retry(timeout_s)
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
                time.sleep(0.025)
                export_func.ready_to_continue.set()
            finally:
                export_thread.join()
                shutdown_thread.join()

        duration = time.time() - start_time
        self.assertLessEqual(duration, timeout_s)
        # pylint: disable=protected-access
        self.assertTrue(exporter._shutdown_event.is_set())
        self.assertIs(export_wrapped.result, result_type.SUCCESS)

    def test_shutdown_timeout_cancels_export_retries(self):
        """Test that shutdown timing out cancels ongoing retries."""

        class ExportFunc:
            is_exporting = threading.Event()
            ready_to_continue = threading.Event()
            mock_export_func = Mock(side_effect=RetryableExportError())

            def __call__(self, *args, **kwargs):
                self.is_exporting.set()
                self.ready_to_continue.wait()
                return self.mock_export_func(*args, **kwargs)

        export_func = ExportFunc()

        exporter = RetryingExporter(export_func, result_type, timeout_s=30)

        class ExportWrap:
            def __init__(self) -> None:
                self.result = None

            def __call__(self, *args, **kwargs):
                self.result = exporter.export_with_retry(30)
                return self.result

        export_wrapped = ExportWrap()

        shutdown_timeout = 1

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
                time.sleep(0)
                export_func.ready_to_continue.set()
            finally:
                export_thread.join()
                shutdown_thread.join()
        duration = time.time() - start_time
        self.assertAlmostEqual(duration, shutdown_timeout, places=1)
        # pylint: disable=protected-access
        self.assertTrue(exporter._shutdown_event.is_set())
        self.assertIs(export_wrapped.result, result_type.FAILURE)
        self.assertEqual(
            warning.records[-1].message,
            "Export cancelled due to shutdown timing out",
        )
