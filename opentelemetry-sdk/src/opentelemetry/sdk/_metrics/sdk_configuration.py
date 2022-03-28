from dataclasses import dataclass
from typing import Sequence

from opentelemetry.sdk._metrics.metric_reader import MetricReader
from opentelemetry.sdk._metrics.view import View
from opentelemetry.sdk.resources import Resource


@dataclass
class SdkConfiguration:
    resource: Resource
    metric_readers: Sequence[MetricReader]
    views: Sequence[View]
