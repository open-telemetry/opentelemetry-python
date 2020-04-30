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
from typing import Union

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


def _load_provider(provider: str) -> Union["TracerProvider", "MeterProvider"]:  # type: ignore
    try:
        return next(  # type: ignore
            iter_entry_points(
                "opentelemetry_{}".format(provider),
                name=getattr(  # type: ignore
                    Configuration(), provider, "default_{}".format(provider),  # type: ignore
                ),
            )
        ).load()()
    except Exception:  # pylint: disable=broad-except
        logger.error(
            "Failed to load configured provider %s", provider,
        )
        raise

# Pattern for matching the 'https://', 'http://', 'ftp://' part.
URL_PATTERN = '^(https?|ftp):\\/\\/'


def disable_tracing_path(url, excluded_paths):
    """Disable tracing on the provided excluded paths

    If the path starts with the excluded path, return True.

    :type excluded_paths: list
    :param excluded_paths: Paths to exclude from tracing

    :rtype: bool
    :returns: True if not tracing, False if tracing
    """
    # Remove the 'https?|ftp://' if exists
    url = re.sub(URL_PATTERN, '', url)

    # Split the url by the first '/' and get the path part
    url_path = url.split('/', 1)[1]

    for path in excluded_paths:
        if url_path.startswith(path):
            return True

    return False


def disable_tracing_hostname(url, excluded_hostnames):
    """Disable tracing for the provided excluded hostnames.

    :type excluded_hostnames: list
    :param excluded_hostnames: hostnames to exclude from tracing

    :rtype: bool
    :returns: True if not tracing, False if tracing
    """
    return url in excluded_hostnames
