from dataclasses import dataclass
from typing import TYPE_CHECKING, Sequence

from opentelemetry.sdk._metrics.metric_reader import MetricReader
from opentelemetry.sdk.resources import Resource

if TYPE_CHECKING:
    from opentelemetry.sdk._metrics.view import View


@dataclass
class SdkConfiguration:
    resource: Resource
    metric_readers: Sequence[MetricReader]
    views: Sequence["View"]
