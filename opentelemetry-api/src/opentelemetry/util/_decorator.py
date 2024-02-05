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

import asyncio
import contextlib
import functools
from typing import Awaitable, Callable, ParamSpec, TypeVar, Iterator

P = ParamSpec("P")
R = TypeVar("R")


class _AgnosticContextManager(
    contextlib._GeneratorContextManager[R]
):

    def __call__(  # type: ignore
        self, func: Callable[P, R | Awaitable[R]]
    ) -> Callable[P, R | Awaitable[R]]:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                with self._recreate_cm():  # type: ignore
                    return await func(*args, **kwargs)  # type: ignore

            return async_wrapper
        else:

            @functools.wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                with self._recreate_cm():  # type: ignore
                    return func(*args, **kwargs)  # type: ignore

            return wrapper


def _agnosticcontextmanager(
    func: Callable[P, Iterator[R]]
) -> Callable[P, _AgnosticContextManager[R]]:
    @functools.wraps(func)
    def helper(*args: P.args, **kwargs: P.kwargs) -> _AgnosticContextManager[R]:
        return _AgnosticContextManager(func, args, kwargs)  # type: ignore

    return helper
