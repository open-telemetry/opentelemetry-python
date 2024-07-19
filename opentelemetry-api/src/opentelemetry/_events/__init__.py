from abc import ABC, abstractmethod
from typing import Any, Optional

from opentelemetry._logs import LogRecord
from opentelemetry._logs.severity import SeverityNumber
from opentelemetry.context.context import Context
from opentelemetry.util.types import Attributes


class Event(LogRecord):

    def __init__(
        self,
        name: str,
        payload: Optional[Any] = None,
        attributes: Optional[Attributes] = None,
    ):
        super().__init__(
            body=payload,  # type: ignore
            attributes=attributes,
        )
        self.name = name


class EventLogger(ABC):

    def __init__(
        self,
        name: str,
        body: Optional[Any] = None,
        timestamp: Optional[int] = None,
        context: Optional[Context] = None,
        severity_number: Optional[SeverityNumber] = None,
        attributes: Optional[Attributes] = None,
    ):
        self._name = name
        self._body = body  # type: ignore
        self._timestamp = timestamp
        self._context = context
        self._severity_number = severity_number
        self._attributes = attributes

    @abstractmethod
    def emit(self, event: "Event") -> None:
        """Emits a :class:`Event` representing an event."""


class EventLoggerProvider(ABC):

    @abstractmethod
    def get_event_logger(
        self,
        name: str,
        version: Optional[str] = None,
        schema_url: Optional[str] = None,
        attributes: Optional[Attributes] = None,
    ) -> EventLogger:
        """Returns an EventLoggerProvider for use."""
