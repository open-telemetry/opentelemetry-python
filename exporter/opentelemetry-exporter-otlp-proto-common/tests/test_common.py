import unittest
import logging

from opentelemetry.exporter.otlp.proto.common._internal import (
    DuplicateFilter,
)


class TestCommonFuncs(unittest.TestCase):

    def test_duplicate_logs_filter_Works(self):
        test_logger = logging.getLogger("testLogger")
        test_logger.addFilter(DuplicateFilter())
        with self.assertLogs('testLogger') as cm:
            test_logger.info("message")
            test_logger.info("message")
        self.assertEqual(len(cm.output), 1)