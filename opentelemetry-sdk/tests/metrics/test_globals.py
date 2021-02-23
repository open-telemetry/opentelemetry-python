# type:ignore
import unittest
from logging import WARNING

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider


class TestGlobals(unittest.TestCase):
    def test_meter_provider_override_warning(self):
        """metrics.set_meter_provider should throw a warning when overridden"""
        metrics.set_meter_provider(MeterProvider())
        with self.assertLogs(level=WARNING) as test:
            metrics.set_meter_provider(MeterProvider())
            self.assertEqual(
                test.output,
                [
                    (
                        "WARNING:opentelemetry.metrics:Overriding of current "
                        "MeterProvider is not allowed"
                    )
                ],
            )
