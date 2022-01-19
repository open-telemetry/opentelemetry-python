from dataclasses import dataclass
from typing import Sequence

from opentelemetry.sdk._metrics.metric_reader import MetricReader
from opentelemetry.sdk.resources import Resource


@dataclass
class SdkConfiguration:
    resource: Resource
    # TODO: once views are added
    # views: Sequence[View]
    metric_readers: Sequence[MetricReader]
