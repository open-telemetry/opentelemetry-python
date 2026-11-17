# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest

from opentelemetry.sdk.logs import LoggerProvider
from opentelemetry.sdk.logs.export import (
    InMemoryLogRecordExporter,
    SimpleLogRecordProcessor,
)


def set_up_logger_provider():
    logger_provider = LoggerProvider()
    exporter = InMemoryLogRecordExporter()
    processor = SimpleLogRecordProcessor(exporter=exporter)
    logger_provider.add_log_record_processor(processor)
    return logger_provider


class TestLoggerProviderCache(unittest.TestCase):
    def test_get_logger_single_name(self):
        logger_provider = set_up_logger_provider()
        # pylint: disable=protected-access
        logger_cache = logger_provider._logger_cache

        # Ensure logger is lazily cached
        self.assertEqual(0, len(logger_cache))

        logger = logger_provider.get_logger("test_logger")
        logger.emit(body="test message")

        self.assertEqual(1, len(logger_cache))

        # Ensure only one logger is cached
        rounds = 100
        for _ in range(rounds):
            logger_provider.get_logger("test_logger").emit(body="test message")

        self.assertEqual(1, len(logger_cache))

    def test_get_logger_multiple_names(self):
        logger_provider = set_up_logger_provider()
        # pylint: disable=protected-access
        logger_cache = logger_provider._logger_cache

        num_loggers = 10
        names = [str(i) for i in range(num_loggers)]

        # Ensure loggers are lazily cached
        self.assertEqual(0, len(logger_cache))

        for name in names:
            logger_provider.get_logger(name).emit(body="test message")

        self.assertEqual(num_loggers, len(logger_cache))

        rounds = 100
        for _ in range(rounds):
            for name in names:
                logger_provider.get_logger(name).emit(body="test message")

        self.assertEqual(num_loggers, len(logger_cache))

    def test_provider_get_logger_no_cache(self):
        logger_provider = set_up_logger_provider()
        # pylint: disable=protected-access
        logger_cache = logger_provider._logger_cache

        logger_provider.get_logger(
            name="test_logger",
            version="version",
            schema_url="schema_url",
            attributes={"key": "value"},
        )

        # Ensure logger is not cached if attributes is set
        self.assertEqual(0, len(logger_cache))

    def test_provider_get_logger_cached(self):
        logger_provider = set_up_logger_provider()
        # pylint: disable=protected-access
        logger_cache = logger_provider._logger_cache

        logger_provider.get_logger(
            name="test_logger",
            version="version",
            schema_url="schema_url",
        )

        # Ensure only one logger is cached
        self.assertEqual(1, len(logger_cache))

        logger_provider.get_logger(
            name="test_logger",
            version="version",
            schema_url="schema_url",
        )

        # Ensure only one logger is cached
        self.assertEqual(1, len(logger_cache))
