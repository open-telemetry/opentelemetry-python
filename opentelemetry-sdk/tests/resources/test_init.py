import unittest

from opentelemetry.sdk import resources


class TestResources(unittest.TestCase):
    def test_resource_merge(self):
        left = resources.Resource({"service": "ui"})
        right = resources.Resource({"host": "service-host"})
        self.assertEqual(
            left.merge(right),
            resources.Resource({
                "service": "ui",
                "host": "service-host"
            }))

    def test_resource_merge_empty_string(self):
        """Verify Resource.merge behavior with the empty string.

        Labels from the source Resource take precedence, with
        the exception of the empty string.

        """
        left = resources.Resource({"service": "ui", "host": ""})
        right = resources.Resource({
            "host": "service-host",
            "service": "not-ui"
        })
        self.assertEqual(
            left.merge(right),
            resources.Resource({
                "service": "ui",
                "host": "service-host"
            }))
