import logging
import unittest
from importlib import reload
from logging import CRITICAL, DEBUG, ERROR, INFO, WARNING
from unittest.mock import patch

from opentelemetry import sdk

sdk_logger = logging.getLogger("opentelemetry.sdk")


def reload_sdk_with_env(env_dict):
    with patch.dict("os.environ", env_dict, clear=True):
        reload(sdk)


class TestLogLevelEnv(unittest.TestCase):
    def tearDown(self):
        """reload sdk to reset logging level"""
        reload(sdk)

    def test_loglevel_is_info_by_default(self):
        reload_sdk_with_env({})
        self.assertEqual(sdk_logger.getEffectiveLevel(), INFO)

    def test_setting_log_level_env_to_valid_value(self):
        valid_value_log_level_pairs = [
            ("DEBUG", DEBUG),
            ("INFO", INFO),
            ("WARNING", WARNING),
            ("ERROR", ERROR),
            ("CRITICAL", CRITICAL),
        ]
        for value, log_level in valid_value_log_level_pairs:
            reload_sdk_with_env({"OTEL_LOG_LEVEL": value})
            self.assertEqual(sdk_logger.getEffectiveLevel(), log_level, value)

    def test_log_level_is_propagated(self):
        reload_sdk_with_env({"OTEL_LOG_LEVEL": "CRITICAL"})
        self.assertEqual(sdk_logger.getEffectiveLevel(), CRITICAL)
        self.assertEqual(
            sdk_logger.getChild("trace").getEffectiveLevel(), CRITICAL
        )
        self.assertEqual(
            sdk_logger.getChild("metrics").getEffectiveLevel(), CRITICAL
        )
        self.assertEqual(
            sdk_logger.getChild("resources").getEffectiveLevel(), CRITICAL
        )

    def test_invalid_log_level_value_warns_and_defaults_to_info(self):
        with self.assertLogs(level=WARNING):
            reload_sdk_with_env({"OTEL_LOG_LEVEL": "NOT_A_VALID_LOG_LEVEL"})
        self.assertEqual(sdk_logger.getEffectiveLevel(), INFO)

    def test_log_level_is_case_insensitive(self):
        reload_sdk_with_env({"OTEL_LOG_LEVEL": "cRiTiCaL"})
        self.assertEqual(sdk_logger.getEffectiveLevel(), CRITICAL)
