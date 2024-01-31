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

from inspect import signature


class OpenTelemetry:
    def __init__(self, *args, **kwargs) -> None:

        args = list(args)

        object.__setattr__(self, "_repr", [])

        parameters = signature(self.__init__).parameters.values()

        for index, parameter in enumerate(parameters):
            if (
                parameter.kind is parameter.POSITIONAL_ONLY
                or parameter.kind is parameter.POSITIONAL_OR_KEYWORD
            ):
                if args:
                    self._repr.append(repr(args.pop(0)))
                else:
                    break
            elif parameter.kind is parameter.VAR_POSITIONAL:
                for _ in range(len(args)):
                    self._repr.append(repr(args.pop(0)))

        for index, parameter in enumerate(parameters):
            if parameter.kind is parameter.KEYWORD_ONLY:
                if args:
                    value = args.pop(0)

                    if parameter.default != value:
                        self._repr.append(f"{parameter.name}={repr(value)}")
                else:
                    break

        for parameter in parameters:
            if (
                parameter.kind is parameter.KEYWORD_ONLY
                or parameter.kind is parameter.POSITIONAL_OR_KEYWORD
            ) and parameter.name in kwargs.keys():
                value = kwargs.pop(parameter.name)

                if parameter.default != value:
                    self._repr.append(f"{parameter.name}={repr(value)}")

            elif parameter.kind is parameter.VAR_KEYWORD:
                for key, value in kwargs.items():
                    self._repr.append(f"{key}={repr(value)}")

        self._repr = f"{self.__class__.__name__}({', '.join(self._repr)})"

    def __repr__(self) -> str:
        return self._repr
