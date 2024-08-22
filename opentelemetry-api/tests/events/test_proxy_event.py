# pylint: disable=W0212,W0222,W0221
import typing
import unittest

import opentelemetry._events as events
from opentelemetry.test.globals_test import EventsGlobalsTest
from opentelemetry.util.types import Attributes


class TestProvider(events.NoOpEventLoggerProvider):
    def get_event_logger(
        self,
        name: str,
        version: typing.Optional[str] = None,
        schema_url: typing.Optional[str] = None,
        attributes: typing.Optional[Attributes] = None,
    ) -> events.EventLogger:
        return LoggerTest(name)


class LoggerTest(events.NoOpEventLogger):
    def emit(self, event: events.Event) -> None:
        pass


class TestProxy(EventsGlobalsTest, unittest.TestCase):
    def test_proxy_logger(self):
        provider = events.get_event_logger_provider()
        # proxy provider
        self.assertIsInstance(provider, events.ProxyEventLoggerProvider)

        # provider returns proxy logger
        event_logger = provider.get_event_logger("proxy-test")
        self.assertIsInstance(event_logger, events.ProxyEventLogger)

        # set a real provider
        events.set_event_logger_provider(TestProvider())

        # get_logger_provider() now returns the real provider
        self.assertIsInstance(events.get_event_logger_provider(), TestProvider)

        # logger provider now returns real instance
        self.assertIsInstance(
            events.get_event_logger_provider().get_event_logger("fresh"),
            LoggerTest,
        )

        # references to the old provider still work but return real logger now
        real_logger = provider.get_event_logger("proxy-test")
        self.assertIsInstance(real_logger, LoggerTest)
