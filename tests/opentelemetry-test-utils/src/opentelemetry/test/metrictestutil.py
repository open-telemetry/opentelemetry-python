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


from opentelemetry.attributes import BoundedAttributes
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    Gauge,
    Metric,
    NumberDataPoint,
    Sum,
)


def _generate_metric(
    name, data, attributes=None, description=None, unit=None
) -> Metric:
    if description is None:
        description = "foo"
    if unit is None:
        unit = "s"
    return Metric(
        name=name,
        description=description,
        unit=unit,
        data=data,
    )


def _generate_sum(
    name,
    value,
    attributes=None,
    description=None,
    unit=None,
    is_monotonic=True,
) -> Metric:
    if attributes is None:
        attributes = BoundedAttributes(attributes={"a": 1, "b": True})
    return _generate_metric(
        name,
        Sum(
            data_points=[
                NumberDataPoint(
                    attributes=attributes,
                    start_time_unix_nano=1641946015139533244,
                    time_unix_nano=1641946016139533244,
                    value=value,
                )
            ],
            aggregation_temporality=AggregationTemporality.CUMULATIVE,
            is_monotonic=is_monotonic,
        ),
        description=description,
        unit=unit,
    )


def _generate_gauge(
    name, value, attributes=None, description=None, unit=None
) -> Metric:
    if attributes is None:
        attributes = BoundedAttributes(attributes={"a": 1, "b": True})
    return _generate_metric(
        name,
        Gauge(
            data_points=[
                NumberDataPoint(
                    attributes=attributes,
                    start_time_unix_nano=1641946015139533244,
                    time_unix_nano=1641946016139533244,
                    value=value,
                )
            ],
        ),
        description=description,
        unit=unit,
    )


def _generate_unsupported_metric(
    name, attributes=None, description=None, unit=None
) -> Metric:
    return _generate_metric(
        name,
        None,
        description=description,
        unit=unit,
    )
