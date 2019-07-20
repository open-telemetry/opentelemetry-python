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
