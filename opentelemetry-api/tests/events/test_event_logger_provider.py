# type:ignore
import unittest
from unittest.mock import Mock, patch

import opentelemetry._events as events
from opentelemetry._events import (
    get_event_logger_provider,
    set_event_logger_provider,
)
from opentelemetry.test.globals_test import EventsGlobalsTest


class TestGlobals(EventsGlobalsTest, unittest.TestCase):
    @patch("opentelemetry._events._logger")
    def test_set_event_logger_provider(self, logger_mock):
        elp_mock = Mock()
        # pylint: disable=protected-access
        self.assertIsNone(events._EVENT_LOGGER_PROVIDER)
        set_event_logger_provider(elp_mock)
        self.assertIs(events._EVENT_LOGGER_PROVIDER, elp_mock)
        self.assertIs(get_event_logger_provider(), elp_mock)
        logger_mock.warning.assert_not_called()

    # pylint: disable=no-self-use
    @patch("opentelemetry._events._logger")
    def test_set_event_logger_provider_will_warn_second_call(
        self, logger_mock
    ):
        elp_mock = Mock()
        set_event_logger_provider(elp_mock)
        set_event_logger_provider(elp_mock)

        logger_mock.warning.assert_called_once_with(
            "Overriding of current EventLoggerProvider is not allowed"
        )

    def test_get_event_logger_provider(self):
        # pylint: disable=protected-access
        self.assertIsNone(events._EVENT_LOGGER_PROVIDER)

        self.assertIsInstance(
            get_event_logger_provider(), events.ProxyEventLoggerProvider
        )

        events._EVENT_LOGGER_PROVIDER = None

        with patch.dict(
            "os.environ",
            {
                "OTEL_PYTHON_EVENT_LOGGER_PROVIDER": "test_event_logger_provider"
            },
        ):
            with patch("opentelemetry._events._load_provider", Mock()):
                with patch(
                    "opentelemetry._events.cast",
                    Mock(**{"return_value": "test_event_logger_provider"}),
                ):
                    self.assertEqual(
                        get_event_logger_provider(),
                        "test_event_logger_provider",
                    )
