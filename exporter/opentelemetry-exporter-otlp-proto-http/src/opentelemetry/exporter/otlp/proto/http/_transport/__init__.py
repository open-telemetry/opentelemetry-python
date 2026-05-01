from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BaseHTTPResult(ABC):
    status_code: int | None = None
    reason: str | None = None
    error: Exception | None = None

    @abstractmethod
    def is_connection_error(self) -> bool: ...


class BaseHTTPTransport(ABC):
    @abstractmethod
    def request(
            self,
            method: str,
            url: str,
            *,
            headers: dict[str, str] | None = None,
            timeout: float | None = None,
            data: bytes | None = None,
    ) -> BaseHTTPResult: ...

    @abstractmethod
    def close(self) -> None: ...
