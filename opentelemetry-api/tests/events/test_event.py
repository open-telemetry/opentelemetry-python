import unittest

from opentelemetry._events import Event


class TestEvent(unittest.TestCase):
    def test_event(self):
        event = Event("example", 123, attributes={"key": "value"})
        self.assertEqual(event.name, "example")
        self.assertEqual(event.timestamp, 123)
        self.assertEqual(
            event.attributes, {"key": "value", "event.name": "example"}
        )

    def test_event_name_copied_in_attributes(self):
        event = Event("name", 123)
        self.assertEqual(event.attributes, {"event.name": "name"})

    def test_event_name_has_precedence_over_attributes(self):
        event = Event("name", 123, attributes={"event.name": "attr value"})
        self.assertEqual(event.attributes, {"event.name": "name"})
