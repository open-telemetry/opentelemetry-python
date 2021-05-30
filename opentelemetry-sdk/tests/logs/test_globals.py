# type:ignore
import unittest
from importlib import reload
from logging import WARNING
from unittest.mock import patch

from opentelemetry.sdk import logs
from opentelemetry.sdk.environment_variables import (
    OTEL_PYTHON_LOG_EMITTER_PROVIDER,
)
from opentelemetry.sdk.logs import (
    LogEmitterProvider,
    get_log_emitter_provider,
    set_log_emitter_provider,
)


class TestGlobals(unittest.TestCase):
    def tearDown(self):
        reload(logs)

    def check_override_not_allowed(self):
        """set_log_emitter_provider should throw a warning when overridden"""
        provider = get_log_emitter_provider()
        with self.assertLogs(level=WARNING) as test:
            set_log_emitter_provider(LogEmitterProvider())
            self.assertEqual(
                test.output,
                [
                    (
                        "WARNING:opentelemetry.sdk.logs:Overriding of current "
                        "LogEmitterProvider is not allowed"
                    )
                ],
            )
        self.assertIs(provider, get_log_emitter_provider())

    def test_tracer_provider_override_warning(self):
        reload(logs)
        self.check_override_not_allowed()

    @patch.dict(
        "os.environ",
        {OTEL_PYTHON_LOG_EMITTER_PROVIDER: "sdk_log_emitter_provider"},
    )
    def test_sdk_log_emitter_provider(self):
        reload(logs)
        self.check_override_not_allowed()

    @patch.dict("os.environ", {OTEL_PYTHON_LOG_EMITTER_PROVIDER: "unknown"})
    def test_unknown_log_emitter_provider(self):
        reload(logs)
        with self.assertRaises(Exception):
            get_log_emitter_provider()
