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

from __future__ import annotations

import logging
from typing import Optional

_logger = logging.getLogger(__name__)


def _parse_headers(
    headers: Optional[list],
    headers_list: Optional[str],
) -> Optional[dict[str, str]]:
    """Merge headers struct and headers_list into a dict.

    Returns None if neither is set, letting the exporter read env vars.
    headers struct takes priority over headers_list for the same key.
    """
    if headers is None and headers_list is None:
        return None
    result: dict[str, str] = {}
    if headers_list:
        for item in headers_list.split(","):
            item = item.strip()
            if "=" in item:
                key, value = item.split("=", 1)
                result[key.strip()] = value.strip()
            elif item:
                _logger.warning(
                    "Invalid header pair in headers_list (missing '='): %s",
                    item,
                )
    if headers:
        for pair in headers:
            result[pair.name] = pair.value or ""
    return result
