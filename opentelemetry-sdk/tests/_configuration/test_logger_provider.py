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

# Tests access private members of SDK classes to assert correct configuration.
# pylint: disable=protected-access

import sys
import unittest
from unittest.mock import MagicMock, patch

from opentelemetry._logs import get_logger_provider
from opentelemetry.sdk._configuration._logger_provider import (
    _DEFAULT_EXPORT_TIMEOUT_MILLIS,
    _DEFAULT_MAX_EXPORT_BATCH_SIZE,
    _DEFAULT_MAX_QUEUE_SIZE,
    _DEFAULT_SCHEDULE_DELAY_MILLIS,
    _create_batch_log_record_processor,
    _create_log_record_exporter,
    _create_log_record_processor,
    _create_simple_log_record_processor,
    configure_logger_provider,
    create_logger_provider,
)
from opentelemetry.sdk._configuration.file._loader import ConfigurationError
from opentelemetry.sdk._configuration.models import (
    BatchLogRecordProcessor as BatchLogRecordProcessorConfig,
)
from opentelemetry.sdk._configuration.models import (
    LoggerProvider as LoggerProviderConfig,
)
from opentelemetry.sdk._configuration.models import (
    LogRecordExporter as LogRecordExporterConfig,
)
from opentelemetry.sdk._configuration.models import (
    LogRecordLimits as LogRecordLimitsConfig,
)
from opentelemetry.sdk._configuration.models import (
    LogRecordProcessor as LogRecordProcessorConfig,
)
from opentelemetry.sdk._configuration.models import (
    NameStringValuePair,
)
from opentelemetry.sdk._configuration.models import (
    OtlpGrpcExporter as OtlpGrpcExporterConfig,
)
from opentelemetry.sdk._configuration.models import (
    OtlpHttpExporter as OtlpHttpExporterConfig,
)
from opentelemetry.sdk._configuration.models import (
    SimpleLogRecordProcessor as SimpleLogRecordProcessorConfig,
)
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs._internal.export import (
    BatchLogRecordProcessor,
    ConsoleLogRecordExporter,
    SimpleLogRecordProcessor,
)
from opentelemetry.sdk.resources import Resource


class TestCreateLoggerProviderBasic(unittest.TestCase):
    def test_none_config_returns_provider(self):
        provider = create_logger_provider(None)
        self.assertIsInstance(provider, LoggerProvider)

    def test_none_config_uses_supplied_resource(self):
        resource = Resource({"service.name": "svc"})
        provider = create_logger_provider(None, resource)
        self.assertIs(provider.resource, resource)

    def test_config_with_no_processors(self):
        config = LoggerProviderConfig(processors=[])
        provider = create_logger_provider(config)
        self.assertIsInstance(provider, LoggerProvider)

    def test_configure_none_is_noop(self):
        original = get_logger_provider()
        configure_logger_provider(None)
        self.assertIs(get_logger_provider(), original)


class TestCreateLogRecordProcessors(unittest.TestCase):
    @staticmethod
    def _make_batch_config(
        exporter_config=None,
        schedule_delay=None,
        export_timeout=None,
        max_queue_size=None,
        max_export_batch_size=None,
    ):
        if exporter_config is None:
            exporter_config = LogRecordExporterConfig(console={})
        return BatchLogRecordProcessorConfig(
            exporter=exporter_config,
            schedule_delay=schedule_delay,
            export_timeout=export_timeout,
            max_queue_size=max_queue_size,
            max_export_batch_size=max_export_batch_size,
        )

    def test_batch_processor_default_schedule_delay(self):
        processor = _create_batch_log_record_processor(
            self._make_batch_config()
        )
        self.assertEqual(
            processor._batch_processor._schedule_delay_millis,
            _DEFAULT_SCHEDULE_DELAY_MILLIS,
        )

    def test_batch_processor_default_export_timeout(self):
        processor = _create_batch_log_record_processor(
            self._make_batch_config()
        )
        self.assertEqual(
            processor._batch_processor._export_timeout_millis,
            _DEFAULT_EXPORT_TIMEOUT_MILLIS,
        )

    def test_batch_processor_default_max_queue_size(self):
        processor = _create_batch_log_record_processor(
            self._make_batch_config()
        )
        self.assertEqual(
            processor._batch_processor._max_queue_size,
            _DEFAULT_MAX_QUEUE_SIZE,
        )

    def test_batch_processor_default_max_export_batch_size(self):
        processor = _create_batch_log_record_processor(
            self._make_batch_config()
        )
        self.assertEqual(
            processor._batch_processor._max_export_batch_size,
            _DEFAULT_MAX_EXPORT_BATCH_SIZE,
        )

    def test_batch_processor_explicit_schedule_delay(self):
        processor = _create_batch_log_record_processor(
            self._make_batch_config(schedule_delay=2000)
        )
        self.assertEqual(
            processor._batch_processor._schedule_delay_millis, 2000.0
        )

    def test_batch_processor_explicit_export_timeout(self):
        processor = _create_batch_log_record_processor(
            self._make_batch_config(export_timeout=5000)
        )
        self.assertEqual(
            processor._batch_processor._export_timeout_millis, 5000.0
        )

    def test_batch_processor_explicit_max_queue_size(self):
        processor = _create_batch_log_record_processor(
            self._make_batch_config(max_queue_size=512)
        )
        self.assertEqual(processor._batch_processor._max_queue_size, 512)

    def test_batch_processor_explicit_max_export_batch_size(self):
        processor = _create_batch_log_record_processor(
            self._make_batch_config(max_export_batch_size=128)
        )
        self.assertEqual(
            processor._batch_processor._max_export_batch_size, 128
        )

    def test_batch_processor_uses_console_exporter(self):
        processor = _create_batch_log_record_processor(
            self._make_batch_config()
        )
        self.assertIsInstance(
            processor._batch_processor._exporter, ConsoleLogRecordExporter
        )

    def test_simple_processor_uses_console_exporter(self):
        config = SimpleLogRecordProcessorConfig(
            exporter=LogRecordExporterConfig(console={})
        )
        processor = _create_simple_log_record_processor(config)
        self.assertIsInstance(processor, SimpleLogRecordProcessor)
        self.assertIsInstance(processor._exporter, ConsoleLogRecordExporter)

    def test_batch_processor_dispatched_from_processor_config(self):
        config = LogRecordProcessorConfig(batch=self._make_batch_config())
        processor = _create_log_record_processor(config)
        self.assertIsInstance(processor, BatchLogRecordProcessor)

    def test_simple_processor_dispatched_from_processor_config(self):
        config = LogRecordProcessorConfig(
            simple=SimpleLogRecordProcessorConfig(
                exporter=LogRecordExporterConfig(console={})
            )
        )
        processor = _create_log_record_processor(config)
        self.assertIsInstance(processor, SimpleLogRecordProcessor)

    def test_no_processor_type_raises(self):
        config = LogRecordProcessorConfig()
        with self.assertRaises(ConfigurationError):
            _create_log_record_processor(config)

    def test_batch_processor_suppresses_env_var(self):
        """schedule_delay default must not read OTEL_BLRP_SCHEDULE_DELAY."""
        with patch.dict("os.environ", {"OTEL_BLRP_SCHEDULE_DELAY": "9999"}):
            processor = _create_batch_log_record_processor(
                self._make_batch_config()
            )
        self.assertEqual(
            processor._batch_processor._schedule_delay_millis,
            _DEFAULT_SCHEDULE_DELAY_MILLIS,
        )


class TestCreateLogRecordExporters(unittest.TestCase):
    def test_console_exporter(self):
        config = LogRecordExporterConfig(console={})
        exporter = _create_log_record_exporter(config)
        self.assertIsInstance(exporter, ConsoleLogRecordExporter)

    def test_otlp_file_development_raises(self):
        config = LogRecordExporterConfig(otlp_file_development={})
        with self.assertRaises(ConfigurationError):
            _create_log_record_exporter(config)

    def test_no_exporter_type_raises(self):
        config = LogRecordExporterConfig()
        with self.assertRaises(ConfigurationError):
            _create_log_record_exporter(config)

    def test_otlp_http_missing_package_raises(self):
        config = LogRecordExporterConfig(
            otlp_http=OtlpHttpExporterConfig(endpoint="http://localhost:4318")
        )
        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.proto.http": None,
                "opentelemetry.exporter.otlp.proto.http._log_exporter": None,
            },
        ):
            with self.assertRaises(ConfigurationError):
                _create_log_record_exporter(config)

    def test_otlp_grpc_missing_package_raises(self):
        config = LogRecordExporterConfig(
            otlp_grpc=OtlpGrpcExporterConfig(endpoint="http://localhost:4317")
        )
        with patch.dict(
            sys.modules,
            {
                "grpc": None,
                "opentelemetry.exporter.otlp.proto.grpc._log_exporter": None,
            },
        ):
            with self.assertRaises(ConfigurationError):
                _create_log_record_exporter(config)

    def test_otlp_http_exporter_endpoint(self):
        mock_exporter_cls = MagicMock()
        mock_compression_cls = MagicMock()
        mock_compression_cls.Gzip = "gzip"

        mock_module = MagicMock()
        mock_module.Compression = mock_compression_cls
        mock_log_module = MagicMock()
        mock_log_module.OTLPLogExporter = mock_exporter_cls

        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.proto.http": mock_module,
                "opentelemetry.exporter.otlp.proto.http._log_exporter": mock_log_module,
            },
        ):
            config = LogRecordExporterConfig(
                otlp_http=OtlpHttpExporterConfig(
                    endpoint="http://collector:4318",
                    timeout=5000,
                )
            )
            _create_log_record_exporter(config)

        mock_exporter_cls.assert_called_once()
        call_kwargs = mock_exporter_cls.call_args.kwargs
        self.assertEqual(call_kwargs["endpoint"], "http://collector:4318")
        self.assertAlmostEqual(call_kwargs["timeout"], 5.0)

    def test_otlp_http_exporter_headers(self):
        mock_exporter_cls = MagicMock()
        mock_compression_cls = MagicMock()
        mock_module = MagicMock()
        mock_module.Compression = mock_compression_cls
        mock_log_module = MagicMock()
        mock_log_module.OTLPLogExporter = mock_exporter_cls

        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.proto.http": mock_module,
                "opentelemetry.exporter.otlp.proto.http._log_exporter": mock_log_module,
            },
        ):
            config = LogRecordExporterConfig(
                otlp_http=OtlpHttpExporterConfig(
                    headers=[
                        NameStringValuePair(name="x-api-key", value="secret")
                    ]
                )
            )
            _create_log_record_exporter(config)

        call_kwargs = mock_exporter_cls.call_args.kwargs
        self.assertEqual(call_kwargs["headers"], {"x-api-key": "secret"})

    def test_otlp_http_exporter_deflate_compression(self):
        mock_exporter_cls = MagicMock()
        mock_compression_cls = MagicMock()
        mock_compression_cls.Deflate = "deflate"
        mock_module = MagicMock()
        mock_module.Compression = mock_compression_cls
        mock_log_module = MagicMock()
        mock_log_module.OTLPLogExporter = mock_exporter_cls

        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.proto.http": mock_module,
                "opentelemetry.exporter.otlp.proto.http._log_exporter": mock_log_module,
            },
        ):
            config = LogRecordExporterConfig(
                otlp_http=OtlpHttpExporterConfig(compression="deflate")
            )
            _create_log_record_exporter(config)

        call_kwargs = mock_exporter_cls.call_args.kwargs
        self.assertEqual(call_kwargs["compression"], "deflate")

    def test_otlp_grpc_exporter_endpoint(self):
        mock_exporter_cls = MagicMock()
        mock_grpc = MagicMock()
        mock_grpc.Compression = MagicMock()
        mock_grpc_log_module = MagicMock()
        mock_grpc_log_module.OTLPLogExporter = mock_exporter_cls

        with patch.dict(
            sys.modules,
            {
                "grpc": mock_grpc,
                "opentelemetry.exporter.otlp.proto.grpc._log_exporter": mock_grpc_log_module,
            },
        ):
            config = LogRecordExporterConfig(
                otlp_grpc=OtlpGrpcExporterConfig(
                    endpoint="http://collector:4317",
                    timeout=10000,
                )
            )
            _create_log_record_exporter(config)

        mock_exporter_cls.assert_called_once()
        call_kwargs = mock_exporter_cls.call_args.kwargs
        self.assertEqual(call_kwargs["endpoint"], "http://collector:4317")
        self.assertAlmostEqual(call_kwargs["timeout"], 10.0)


class TestLogRecordLimits(unittest.TestCase):
    def test_limits_logs_warning(self):
        config = LoggerProviderConfig(
            processors=[],
            limits=LogRecordLimitsConfig(attribute_count_limit=64),
        )
        with self.assertLogs(
            "opentelemetry.sdk._configuration._logger_provider",
            level="WARNING",
        ) as cm:
            create_logger_provider(config)
        self.assertTrue(
            any("limits" in msg for msg in cm.output),
            "Expected warning about unsupported limits",
        )

    @staticmethod
    def test_no_limits_no_warning():
        config = LoggerProviderConfig(processors=[])
        with patch(
            "opentelemetry.sdk._configuration._logger_provider._logger"
        ) as mock_logger:
            create_logger_provider(config)
            mock_logger.warning.assert_not_called()


if __name__ == "__main__":
    unittest.main()
