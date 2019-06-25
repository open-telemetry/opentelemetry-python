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


"""
The OpenTelemetry backend module defines and implements the API to access an
implementation (backend) of the OpenTelemetry API.
"""

from typing import Callable, Any
import traceback
import sys
import os
import importlib

from .trace import Tracer

# REMOVE {{{
# Callback that creates the default implementation
_PROVIDER: Callable[[type], object] = None

_PROVIDER_TB: str = None

def register_provider(set_provider_cb: Callable):
    global _PROVIDER # pylint:disable=global-statement
    global _PROVIDER_TB # pylint:disable=global-statement

    if _PROVIDER:
        raise ValueError(
            "A provider was already registered. Original"
            " registration's traceback: " + str(_PROVIDER_TB))
    assert _PROVIDER_TB is None, 'Inconsistent state: ' + str(_PROVIDER_TB)
    _PROVIDER_TB = ''.join(traceback.format_stack())
    if _IMPLEMENTATION:
        _PROVIDER = True
    else:
        _PROVIDER = set_provider_cb
# }}}

DEFAULT_BACKEND_MODNAME = 'opentelemetry.sdk.internal.backend_impl'

def _get_fallback_impl(type_: type) -> Any:
    """Gets the fallback implementation for `type_`.

    `type_` must be a OpenTelemetry API type like `Tracer`.

    First, the function tries to find a module that provides a `get_opentelemetry_backend_impl`
    function (with the same signature as this function). The following modules are tried:

    1. `$OPENTELEMETRY_PYTHON_BACKEND_<typename>` (e.g. `OPENTELEMETRY_PYTHON_BACKEND_TRACER`)
    2. `$OPENTELEMETRY_PYTHON_BACKEND_DEFAULT` (e.g. `OPENTELEMETRY_PYTHON_BACKEND_TRACER`)
    3. The OpenTelemetry SDK's tracer module.

    Note that if any of the environment variables is set to an nonempty value, further steps
    are not tried, even if the modulename set there is invalid or fails to load. The no-op API
    implementation is returned instead.
    """
    if not sys.flags.ignore_environment:
        backend_modname = os.getenv('OPENTELEMETRY_PYTHON_BACKEND_' + type_.__name__.upper())
        if not backend_modname:
            backend_modname = os.getenv('OPENTELEMETRY_PYTHON_BACKEND_DEFAULT')
            if not backend_modname:
                backend_modname = DEFAULT_BACKEND_MODNAME
        if backend_modname:
            try:
                backend_mod = importlib.import_module(backend_modname)
            except (ImportError, SyntaxError):
                # TODO Log/warn
                return type_()
            try:
                backend_fn = getattr(backend_mod, 'get_backend_impl')
            except AttributeError:
                # TODO Log/warn
                return type_()
            result = backend_fn(type_)
            if not result:
                # This is an expected case.
                return type_()
            # TODO: Warn if backend_fn returns type_(): It should return None to indicate using the
            # default.




def get_tracer() -> Tracer:
    return _selectimpl(Tracer)
