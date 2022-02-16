from dataclasses import dataclass, field
from threading import Lock
from typing import TYPE_CHECKING, Sequence, Tuple

from opentelemetry.sdk._metrics.metric_reader import MetricReader
from opentelemetry.sdk._metrics.view import View
from opentelemetry.sdk.resources import Resource

if TYPE_CHECKING:
    from opentelemetry.sdk._metrics.instrument import _Asynchronous


@dataclass
class SdkConfiguration:
    resource: Resource
    metric_readers: Sequence[MetricReader]
    views: Sequence[View]
    _async_instruments: Tuple["_Asynchronous", ...] = ()
    _lock: Lock = field(default_factory=Lock)

    @property
    def async_instruments(self) -> Sequence["_Asynchronous"]:
        """Thread safe context manager giving access to the list"""
        return self._async_instruments

    def add_async_instrument(self, instrument: "_Asynchronous") -> None:
        with self._lock:
            self._async_instruments += (instrument,)
