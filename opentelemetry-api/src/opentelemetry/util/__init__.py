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
import re
import time
from logging import getLogger
from typing import TYPE_CHECKING, Sequence, Union, cast

from pkg_resources import iter_entry_points

from opentelemetry.configuration import Configuration

if TYPE_CHECKING:
    from opentelemetry.metrics import MeterProvider
    from opentelemetry.trace import TracerProvider

Provider = Union["TracerProvider", "MeterProvider"]

logger = getLogger(__name__)

# Since we want API users to be able to provide timestamps,
# this needs to be in the API.

try:
    time_ns = time.time_ns
# Python versions < 3.7
except AttributeError:

    def time_ns() -> int:
        return int(time.time() * 1e9)


def _load_provider(provider: str) -> Provider:
    try:
        entry_point = next(
            iter_entry_points(
                "opentelemetry_{}".format(provider),
                name=cast(
                    str,
                    Configuration().get(
                        provider.upper(), "default_{}".format(provider),
                    ),
                ),
            )
        )
        return cast(Provider, entry_point.load()(),)
    except Exception:  # pylint: disable=broad-except
        logger.error("Failed to load configured provider %s", provider)
        raise


def _load_meter_provider(provider: str) -> "MeterProvider":
    return cast("MeterProvider", _load_provider(provider))


def _load_trace_provider(provider: str) -> "TracerProvider":
    return cast("TracerProvider", _load_provider(provider))
