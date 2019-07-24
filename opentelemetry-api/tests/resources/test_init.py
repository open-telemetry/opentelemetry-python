import unittest
from opentelemetry.resources import Resource


class TestResources(unittest.TestCase):
    @staticmethod
    def test_resource_merge():
        left = Resource({"service": "ui"})
        right = Resource({"host": "service-host"})
        assert left.merge(right) == Resource(
            {"service": "ui", "host": "service-host"}
        )

    @staticmethod
    def test_resource_merge_empty_string():
        """
        labels from the source Resource take
        precedence, with the exception of the empty string.
        """
        left = Resource({"service": "ui", "host": ""})
        right = Resource({"host": "service-host", "service": "not-ui"})
        assert left.merge(right) == Resource(
            {"service": "ui", "host": "service-host"}
        )
