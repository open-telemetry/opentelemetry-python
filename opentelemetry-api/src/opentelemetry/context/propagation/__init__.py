# Copyright 2019, OpenTelemetry Authors
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
import typing

from opentelemetry.context import Context

from .binaryformat import BinaryFormat
from .httptextformat import (
    ContextT,
    DefaultHTTPExtractor,
    DefaultHTTPInjector,
    Getter,
    HTTPExtractor,
    HTTPInjector,
    Setter,
)

__all__ = [
    "BinaryFormat",
    "ContextT",
    "Getter",
    "DefaultHTTPExtractor",
    "DefaultHTTPInjector",
    "HTTPExtractor",
    "HTTPInjector",
    "Setter",
]


def get_as_list(
    dict_object: typing.Dict[str, str], key: str
) -> typing.List[str]:
    value = dict_object.get(key)
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def set_in_dict(
    dict_object: typing.Dict[str, str], key: str, value: str
) -> None:
    dict_object[key] = value
