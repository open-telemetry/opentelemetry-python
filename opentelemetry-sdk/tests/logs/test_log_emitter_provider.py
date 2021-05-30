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

# pylint:disable=protected-access,no-self-use

import logging
import shutil
import subprocess
import threading
import unittest
from unittest.mock import MagicMock, Mock

from opentelemetry.sdk import logs, trace
from opentelemetry.sdk.logs import (
    ConcurrentMultiLogProcessor,
    LogEmitterProvider,
    LogProcessor,
    SynchronousMultiLogProcessor,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationInfo
from opentelemetry.trace.span import INVALID_SPAN_CONTEXT


class CustomLogProcessor(LogProcessor):
    def __init__(self, exporter):
        self._exporter = exporter
        self._logs = []
        self._lock = threading.Lock()
        self._closed = False

    def emit(self, log_data):
        if self._closed:
            return
        with self._lock:
            self._logs.append(log_data)
            if len(self._logs) % 100 == 0:
                self._export()

    def _export(self):
        self._exporter.export(self._logs)
        self._logs.clear()

    def shutdown(self):
        self._closed = True

    def force_flush(self, timeout_millis=30000):
        with self._lock:
            self._export()
        return True


class TestLogEmitterProvider(unittest.TestCase):
    def test_log_emitter_provider_defaults(self):
        provider = LogEmitterProvider()
        self.assertEqual(provider._resource, Resource.create())
        self.assertIsInstance(provider._multi_log_processor, logs.LogProcessor)
        self.assertIsNotNone(provider._at_exit_handler)

    def test_log_emitter_provider_emitter(self):
        resource = Resource.create({"service.name": "service-name"})
        provider = LogEmitterProvider(resource)
        log_emitter = provider.get_log_emitter("name", "v-1.0")
        self.assertIsInstance(log_emitter, logging.Handler)
        self.assertEqual(log_emitter._resource, resource)
        expected = InstrumentationInfo("name", "v-1.0")
        self.assertEqual(log_emitter._instrumentation_info, expected)

    def test_log_emitter_provider_add_processor(self):
        multi_log_processor, exporter = MagicMock(), MagicMock()
        provider = LogEmitterProvider(multi_log_processor=multi_log_processor)
        custom_processor = CustomLogProcessor(exporter)
        provider.add_log_processor(custom_processor)
        multi_log_processor.add_log_processor.assert_called()
        multi_log_processor.add_log_processor.assert_called_with(
            custom_processor
        )

    def test_log_emitter_provider_accepts_multi_log_processors(self):
        sync_multi_log_processor = SynchronousMultiLogProcessor()
        provider = LogEmitterProvider(
            multi_log_processor=sync_multi_log_processor
        )
        self.assertEqual(
            provider._multi_log_processor, sync_multi_log_processor
        )
        concurrent_multi_log_processor = ConcurrentMultiLogProcessor()
        provider = LogEmitterProvider(
            multi_log_processor=concurrent_multi_log_processor
        )
        self.assertEqual(
            provider._multi_log_processor, concurrent_multi_log_processor
        )

    def test_shutdown(self):
        provider = LogEmitterProvider()
        mock_processor_1 = MagicMock()
        mock_processor_1.mock_add_spec(spec=LogProcessor)
        provider.add_log_processor(mock_processor_1)
        mock_processor_2 = MagicMock()
        mock_processor_2.mock_add_spec(spec=LogProcessor)
        provider.add_log_processor(mock_processor_2)

        provider.shutdown()
        self.assertEqual(mock_processor_1.shutdown.call_count, 1)
        self.assertEqual(mock_processor_2.shutdown.call_count, 1)

        atexit_handler_code = """
import atexit
from unittest import mock

from opentelemetry.sdk.logs import LogEmitterProvider, LogProcessor

mock_processor = mock.Mock(spec=LogProcessor)

def print_shutdown_count():
    print(mock_processor.shutdown.call_count)

# atexit hooks are called in inverse order they are added, so do this before
# creating the log emitter
atexit.register(print_shutdown_count)

log_emitter_provider = LogEmitterProvider({emitter_parameters})
log_emitter_provider.add_log_processor(mock_processor)

{emitter_shutdown}
"""

        def run_code(shutdown_on_exit, explicit_shutdown):
            emitter_params = ""
            emitter_shutdown = ""
            if not shutdown_on_exit:
                emitter_params = "shutdown_on_exit=False"

            if explicit_shutdown:
                emitter_shutdown = "log_emitter_provider.shutdown()"

            return subprocess.check_output(
                [
                    # use shutil to avoid calling python outside the
                    # virtualenv on windows.
                    shutil.which("python"),
                    "-c",
                    atexit_handler_code.format(
                        emitter_parameters=emitter_params,
                        emitter_shutdown=emitter_shutdown,
                    ),
                ]
            )

        # test default shutdown_on_exit (True)
        out = run_code(True, False)
        self.assertTrue(out.startswith(b"1"))

        # test that shutdown is called only once even if shutdown is
        # called explicitely
        out = run_code(True, True)
        self.assertTrue(out.startswith(b"1"))

        # test shutdown_on_exit=False
        out = run_code(False, False)
        self.assertTrue(out.startswith(b"0"))


class TestLogEmitter(unittest.TestCase):
    def test_log_emitter_simple(self):
        multi_log_processor = Mock()
        provider = LogEmitterProvider(multi_log_processor=multi_log_processor)
        emitter = provider.get_log_emitter("name", "v-2.0")

        logger = logging.getLogger("simple")
        logger.addHandler(emitter)

        logger.warning("Warning message")
        multi_log_processor.emit.assert_called_once()

    def test_log_emitter_custom_level(self):
        multi_log_processor = Mock()
        provider = LogEmitterProvider(multi_log_processor=multi_log_processor)
        emitter = provider.get_log_emitter("name", "v-2.0")

        logger = logging.getLogger("custom_level_emitter")
        logger.addHandler(emitter)
        logger.setLevel(logging.ERROR)

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

        self.assertEqual(multi_log_processor.emit.call_count, 2)

    def test_log_emitter_instrumentation_info(self):
        multi_log_processor = Mock()
        provider = LogEmitterProvider(multi_log_processor=multi_log_processor)
        emitter = provider.get_log_emitter("name", "v-2.0")

        expected = InstrumentationInfo("name", "v-2.0")
        self.assertEqual(emitter._instrumentation_info, expected)

    def test_log_emitter_without_trace_correlation(self):
        custom_processor = CustomLogProcessor(Mock())
        provider = LogEmitterProvider()
        provider.add_log_processor(custom_processor)
        emitter = provider.get_log_emitter("name", "version")

        logger = logging.getLogger("no.trace.correlation")
        logger.addHandler(emitter)

        logger.critical("Oh no!!")
        critical_log = custom_processor._logs[0].log_record

        self.assertEqual(critical_log.trace_id, INVALID_SPAN_CONTEXT.trace_id)
        self.assertEqual(critical_log.span_id, INVALID_SPAN_CONTEXT.span_id)
        self.assertEqual(
            critical_log.trace_flags, INVALID_SPAN_CONTEXT.trace_flags
        )

    def test_log_emitter_with_trace_correlation(self):
        custom_processor = CustomLogProcessor(Mock())
        provider = LogEmitterProvider()
        provider.add_log_processor(custom_processor)
        emitter = provider.get_log_emitter("name", "version")

        logger = logging.getLogger("with.trace.correlation")
        logger.addHandler(emitter)

        tracer = trace.TracerProvider().get_tracer(__name__)
        with tracer.start_as_current_span("test") as span:
            logger.critical("Critical message within span")
            span_context = span.get_span_context()
            critical_log = custom_processor._logs[0].log_record

            self.assertEqual(critical_log.trace_id, span_context.trace_id)
            self.assertEqual(critical_log.span_id, span_context.span_id)
            self.assertEqual(
                critical_log.trace_flags, span_context.trace_flags
            )
