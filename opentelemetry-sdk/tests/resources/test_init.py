import unittest
from opentelemetry.sdk.resources import DefaultResource


class TestResources(unittest.TestCase):
    def test_resource_merge(self):
        left = DefaultResource({"service": "ui"})
        right = DefaultResource({"host": "service-host"})
        self.assertEqual(
            left.merge(right),
            DefaultResource({
                "service": "ui",
                "host": "service-host"
            }))

    def test_resource_merge_empty_string(self):
        """
        labels from the source Resource take
        precedence, with the exception of the empty string.
        """
        left = DefaultResource({"service": "ui", "host": ""})
        right = DefaultResource({"host": "service-host", "service": "not-ui"})
        self.assertEqual(
            left.merge(right),
            DefaultResource({
                "service": "ui",
                "host": "service-host"
            }))
