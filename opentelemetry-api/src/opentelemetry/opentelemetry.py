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

        object.__setattr__(self, "_args", list(args))
        object.__setattr__(self, "_kwargs", kwargs)
        object.__setattr__(self, "_repr", None)

    def __repr__(self) -> str:

        if self._repr is not None:
            return self._repr

        repr_ = []

        parameters = signature(self.__init__).parameters.values()

        for index, parameter in enumerate(parameters):
            if (
                parameter.kind is parameter.POSITIONAL_ONLY
                or parameter.kind is parameter.POSITIONAL_OR_KEYWORD
            ):
                if self._args:
                    repr_.append(repr(self._args.pop(0)))
                else:
                    break
            elif parameter.kind is parameter.VAR_POSITIONAL:
                for _ in range(len(self._args)):
                    repr_.append(repr(self._args.pop(0)))

        for index, parameter in enumerate(parameters):
            if parameter.kind is parameter.KEYWORD_ONLY:
                if self._args:
                    value = self._args.pop(0)

                    if parameter.default != value:
                        repr_.append(f"{parameter.name}={repr(value)}")
                else:
                    break

        for parameter in parameters:
            if (
                parameter.kind is parameter.KEYWORD_ONLY
                or parameter.kind is parameter.POSITIONAL_OR_KEYWORD
            ) and parameter.name in self._kwargs.keys():
                value = self._kwargs.pop(parameter.name)

                if parameter.default != value:
                    repr_.append(f"{parameter.name}={repr(value)}")

            elif parameter.kind is parameter.VAR_KEYWORD:
                for key, value in self._kwargs.items():
                    repr_.append(f"{key}={repr(value)}")

        object.__setattr__(
            self, "_repr", f"{self.__class__.__name__}({', '.join(repr_)})"
        )

        return self._repr
