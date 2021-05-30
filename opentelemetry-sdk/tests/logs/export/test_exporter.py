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

# pylint: disable=protected-access
import logging
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

from opentelemetry.sdk import trace
from opentelemetry.sdk.logs import LogEmitterProvider
from opentelemetry.sdk.logs.export import BatchLogProcessor, SimpleLogProcessor
from opentelemetry.sdk.logs.export.in_memory_log_exporter import (
    InMemoryLogExporter,
)
from opentelemetry.sdk.logs.severity import SeverityNumber
from opentelemetry.trace.span import INVALID_SPAN_CONTEXT


class TestSimpleLogProcessor(unittest.TestCase):
    def test_simple_log_processor_default_level(self):
        exporter = InMemoryLogExporter()
        log_emitter_provider = LogEmitterProvider()
        log_emitter = log_emitter_provider.get_log_emitter(__name__)

        log_emitter_provider.add_log_processor(SimpleLogProcessor(exporter))

        logger = logging.getLogger("default_level")
        logger.addHandler(log_emitter)

        logger.warning("Something is wrong")
        finished_logs = exporter.get_finished_logs()
        self.assertEqual(len(finished_logs), 1)
        warning_log_record = finished_logs[0].log_record
        self.assertEqual(warning_log_record.body, "Something is wrong")
        self.assertEqual(warning_log_record.severity_text, "WARNING")
        self.assertEqual(
            warning_log_record.severity_number, SeverityNumber.WARN
        )

    def test_simple_log_processor_custom_level(self):
        exporter = InMemoryLogExporter()
        log_emitter_provider = LogEmitterProvider()
        log_emitter = log_emitter_provider.get_log_emitter(__name__)

        log_emitter_provider.add_log_processor(SimpleLogProcessor(exporter))

        logger = logging.getLogger("custom_level")
        logger.setLevel(logging.ERROR)
        logger.addHandler(log_emitter)

        logger.warning("Warning message")
        logger.debug("Debug message")
        logger.error("Error message")
        logger.critical("Critical message")
        finished_logs = exporter.get_finished_logs()
        # Make sure only level >= logging.CRITICAL logs are recorded
        self.assertEqual(len(finished_logs), 2)
        critical_log_record = finished_logs[0].log_record
        fatal_log_record = finished_logs[1].log_record
        self.assertEqual(critical_log_record.body, "Error message")
        self.assertEqual(critical_log_record.severity_text, "ERROR")
        self.assertEqual(
            critical_log_record.severity_number, SeverityNumber.ERROR
        )
        self.assertEqual(fatal_log_record.body, "Critical message")
        self.assertEqual(fatal_log_record.severity_text, "CRITICAL")
        self.assertEqual(
            fatal_log_record.severity_number, SeverityNumber.FATAL
        )

    def test_simple_log_processor_trace_correlation(self):
        exporter = InMemoryLogExporter()
        log_emitter_provider = LogEmitterProvider()
        log_emitter = log_emitter_provider.get_log_emitter("name", "version")

        log_emitter_provider.add_log_processor(SimpleLogProcessor(exporter))

        logger = logging.getLogger("trace_correlation")
        logger.addHandler(log_emitter)

        logger.warning("Warning message")
        finished_logs = exporter.get_finished_logs()
        self.assertEqual(len(finished_logs), 1)
        log_record = finished_logs[0].log_record
        self.assertEqual(log_record.body, "Warning message")
        self.assertEqual(log_record.severity_text, "WARNING")
        self.assertEqual(log_record.severity_number, SeverityNumber.WARN)
        self.assertEqual(log_record.trace_id, INVALID_SPAN_CONTEXT.trace_id)
        self.assertEqual(log_record.span_id, INVALID_SPAN_CONTEXT.span_id)
        self.assertEqual(
            log_record.trace_flags, INVALID_SPAN_CONTEXT.trace_flags
        )
        exporter.clear()

        tracer = trace.TracerProvider().get_tracer(__name__)
        with tracer.start_as_current_span("test") as span:
            logger.critical("Critical message within span")

            finished_logs = exporter.get_finished_logs()
            log_record = finished_logs[0].log_record
            self.assertEqual(log_record.body, "Critical message within span")
            self.assertEqual(log_record.severity_text, "CRITICAL")
            self.assertEqual(log_record.severity_number, SeverityNumber.FATAL)
            span_context = span.get_span_context()
            self.assertEqual(log_record.trace_id, span_context.trace_id)
            self.assertEqual(log_record.span_id, span_context.span_id)
            self.assertEqual(log_record.trace_flags, span_context.trace_flags)

    def test_simple_log_processor_shutdown(self):
        exporter = InMemoryLogExporter()
        log_emitter_provider = LogEmitterProvider()
        log_emitter = log_emitter_provider.get_log_emitter(__name__)

        log_emitter_provider.add_log_processor(SimpleLogProcessor(exporter))

        logger = logging.getLogger("shutdown")
        logger.addHandler(log_emitter)

        logger.warning("Something is wrong")
        finished_logs = exporter.get_finished_logs()
        self.assertEqual(len(finished_logs), 1)
        warning_log_record = finished_logs[0].log_record
        self.assertEqual(warning_log_record.body, "Something is wrong")
        self.assertEqual(warning_log_record.severity_text, "WARNING")
        self.assertEqual(
            warning_log_record.severity_number, SeverityNumber.WARN
        )
        exporter.clear()
        log_emitter_provider.shutdown()
        logger.warning("Log after shutdown")
        finished_logs = exporter.get_finished_logs()
        self.assertEqual(len(finished_logs), 0)


class TestBatchLogProcessor(unittest.TestCase):
    def test_emit_call_log_record(self):
        exporter = InMemoryLogExporter()
        log_processor = Mock(wraps=BatchLogProcessor(exporter))
        provider = LogEmitterProvider()
        provider.add_log_processor(log_processor)

        emitter = provider.get_log_emitter(__name__)
        logger = logging.getLogger("emit_call")
        logger.addHandler(emitter)

        logger.error("error")
        self.assertEqual(log_processor.emit.call_count, 1)

    def test_shutdown(self):
        exporter = InMemoryLogExporter()
        log_processor = BatchLogProcessor(exporter)

        provider = LogEmitterProvider()
        provider.add_log_processor(log_processor)

        emitter = provider.get_log_emitter(__name__)
        logger = logging.getLogger("shutdown")
        logger.addHandler(emitter)

        logger.warning("warning message: %s", "possible upcoming heatwave")
        logger.error("Very high rise in temperatures across the globe")
        logger.critical("Temparature hits high 420 C and all humans are dead")

        log_processor.shutdown()
        self.assertTrue(exporter._stopped)

        finished_logs = exporter.get_finished_logs()
        expected = [
            ("warning message: possible upcoming heatwave", "WARNING"),
            ("Very high rise in temperatures across the globe", "ERROR"),
            (
                "Temparature hits high 420 C and all humans are dead",
                "CRITICAL",
            ),
        ]
        emitted = [
            (item.log_record.body, item.log_record.severity_text)
            for item in finished_logs
        ]
        self.assertEqual(expected, emitted)

    def test_force_flush(self):
        exporter = InMemoryLogExporter()
        log_processor = BatchLogProcessor(exporter)

        provider = LogEmitterProvider()
        provider.add_log_processor(log_processor)

        emitter = provider.get_log_emitter(__name__)
        logger = logging.getLogger("force_flush")
        logger.addHandler(emitter)

        logger.critical("Earth is burning")
        log_processor.force_flush()
        finished_logs = exporter.get_finished_logs()
        self.assertEqual(len(finished_logs), 1)
        log_record = finished_logs[0].log_record
        self.assertEqual(log_record.body, "Earth is burning")
        self.assertEqual(log_record.severity_number, SeverityNumber.FATAL)

    def test_log_processor_too_many_logs(self):
        exporter = InMemoryLogExporter()
        log_processor = BatchLogProcessor(exporter)

        provider = LogEmitterProvider()
        provider.add_log_processor(log_processor)

        emitter = provider.get_log_emitter(__name__)
        logger = logging.getLogger("many_logs")
        logger.addHandler(emitter)

        for log_no in range(1000):
            logger.critical("Log no: %s", log_no)

        self.assertTrue(log_processor.force_flush())
        finised_logs = exporter.get_finished_logs()
        self.assertEqual(len(finised_logs), 1000)

    def test_with_multiple_threads(self):
        exporter = InMemoryLogExporter()
        log_processor = BatchLogProcessor(exporter)

        provider = LogEmitterProvider()
        provider.add_log_processor(log_processor)

        emitter = provider.get_log_emitter(__name__)
        logger = logging.getLogger("threads")
        logger.addHandler(emitter)

        def bulk_log_and_flush(num_logs):
            for _ in range(num_logs):
                logger.critical("Critical message")
            self.assertTrue(log_processor.force_flush())

        with ThreadPoolExecutor(max_workers=69) as executor:
            futures = []
            for idx in range(69):
                future = executor.submit(bulk_log_and_flush, idx + 1)
                futures.append(future)

            executor.shutdown()

        finished_logs = exporter.get_finished_logs()
        self.assertEqual(len(finished_logs), 2415)
