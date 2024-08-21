import unittest

from opentelemetry._events import Event


class TestEvent(unittest.TestCase):
    def test_event(self):
        event = Event("example", 123, attributes={"key": "value"})
        self.assertEqual(event.name, "example")
        self.assertEqual(event.timestamp, 123)
        self.assertEqual(event.attributes, {"key": "value", "event.name": "example"})
