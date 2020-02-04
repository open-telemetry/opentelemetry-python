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

from opentelemetry.context.context import Context


class DefaultContext(Context):
    def __init__(self) -> None:
        self.values = {}  # type: typing.Dict[str, object]

    def set_value(self, key: str, value: "object") -> None:
        """Set a value in this context"""
        self.values[key] = value

    def get_value(self, key: str) -> "object":
        """Get a value from this context"""
        return self.values.get(key)

    def remove_value(self, key: str) -> None:
        """Remove a value from this context"""
        if key in self.values:
            self.values.pop(key)


__all__ = ["DefaultContext"]
