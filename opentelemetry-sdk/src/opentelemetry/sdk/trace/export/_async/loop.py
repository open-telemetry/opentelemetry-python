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
from functools import wraps
from logging import getLogger
from typing import Callable, Awaitable, Optional, ParamSpec, TypeVar
from opentelemetry.util._once import Once
from threading import current_thread, Thread
from concurrent.futures import Future

_logger = getLogger(__name__)

_event_loop: Optional[asyncio.AbstractEventLoop] = None
_create_loop_once = Once()


def _create() -> None:
    loop = asyncio.new_event_loop()
    global _event_loop
    _event_loop = loop

    def thread() -> None:
        try:
            _logger.info("Starting loop in thread %s", current_thread())
            loop.run_forever()
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    Thread(
        name="OTelSharedAsyncioLoopThread", target=thread, daemon=True
    ).start()


def get_otel_event_loop() -> asyncio.AbstractEventLoop:
    """Shared event loop used by all OpenTelemetry components doing background work

    Currently runs in its own thread, but could run in the user's existing event loop
    """
    # TODO: consider use the existing event loop (asyncio.get_running_loop()) if it is
    # available. This would only work if we add async variants to providers'
    # shutdown/force_flush methods. Otherwise, it will just deadlock the event loop thread.

    _create_loop_once.do_once(_create)
    assert _event_loop is not None
    return _event_loop


P = ParamSpec("P")
R = TypeVar("R")


def run_in_otel_event_loop(
    f: Callable[P, Awaitable[R]]
) -> Callable[P, Future[R]]:
    @wraps(f)
    def wrap(*args: P.args, **kwargs: P.kwargs) -> Future[R]:
        return asyncio.run_coroutine_threadsafe(
            f(*args, **kwargs), get_otel_event_loop()
        )

    return wrap
