# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from collections import OrderedDict

from opentelemetry.attributes import BoundedAttributes
from opentelemetry.sdk._metrics.point import (
    AggregationTemporality,
    Gauge,
    Metric,
    Sum,
)
from opentelemetry.sdk.resources import Resource as SDKResource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope


def _generate_metric(
    name, point, attributes=None, description=None, unit=None
) -> Metric:
    if not attributes:
        attributes = BoundedAttributes(attributes={"a": 1, "b": True})
    if not description:
        description = "foo"
    if not unit:
        unit = "s"
    return Metric(
        resource=SDKResource(OrderedDict([("a", 1), ("b", False)])),
        instrumentation_scope=InstrumentationScope(
            "first_name", "first_version"
        ),
        attributes=attributes,
        description=description,
        name=name,
        unit=unit,
        point=point,
    )


def _generate_sum(
    name, val, attributes=None, description=None, unit=None
) -> Sum:
    return _generate_metric(
        name,
        Sum(
            aggregation_temporality=AggregationTemporality.CUMULATIVE,
            is_monotonic=True,
            start_time_unix_nano=1641946015139533244,
            time_unix_nano=1641946016139533244,
            value=val,
        ),
        attributes=attributes,
        description=description,
        unit=unit,
    )


def _generate_gauge(
    name, val, attributes=None, description=None, unit=None
) -> Gauge:
    return _generate_metric(
        name,
        Gauge(
            time_unix_nano=1641946016139533244,
            value=val,
        ),
        attributes=attributes,
        description=description,
        unit=unit,
    )


def _generate_unsupported_metric(
    name, attributes=None, description=None, unit=None
) -> Sum:
    return _generate_metric(
        name,
        None,
        attributes=attributes,
        description=description,
        unit=unit,
    )
