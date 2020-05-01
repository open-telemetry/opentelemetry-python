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
from typing import Sequence, Union

from pkg_resources import iter_entry_points

from opentelemetry.configuration import Configuration  # type: ignore

logger = getLogger(__name__)

# Since we want API users to be able to provide timestamps,
# this needs to be in the API.

try:
    time_ns = time.time_ns
# Python versions < 3.7
except AttributeError:

    def time_ns() -> int:
        return int(time.time() * 1e9)


def _load_provider(
    provider: str,
) -> Union["TracerProvider", "MeterProvider"]:  # type: ignore
    try:
        return next(  # type: ignore
            iter_entry_points(
                "opentelemetry_{}".format(provider),
                name=getattr(
                    Configuration(),  # type: ignore
                    provider,
                    "default_{}".format(provider),
                ),
            )
        ).load()()
    except Exception:  # pylint: disable=broad-except
        logger.error("Failed to load configured provider %s", provider)
        raise


# Pattern for matching up until the first '/' after the 'https://' part.
_URL_PATTERN = r"(https?|ftp)://.*?/"


def disable_tracing_path(url: str, excluded_paths: Sequence[str]) -> bool:
    if excluded_paths:
        # Match only the part after the first '/' that is not in _URL_PATTERN
        regex = "{}({})".format(_URL_PATTERN, "|".join(excluded_paths))
        if re.match(regex, url):
            return True
    return False


def disable_tracing_hostname(
    url: str, excluded_hostnames: Sequence[str]
) -> bool:
    return url in excluded_hostnames
