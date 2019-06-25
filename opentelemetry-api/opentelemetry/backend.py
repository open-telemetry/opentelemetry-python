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

import sys
import os
import importlib
from typing import TypeVar, Type, Callable
from functools import wraps

from .trace import Tracer

### Generic private code {{{1

_T = TypeVar('_T')

_DEFAULT_BACKEND_MODNAME = 'opentelemetry.sdk.internal.backend_impl'
_UNIT_TEST_IGNORE_ENV = False

_tracer = None

def _get_fallback_impl(api_type: Type[_T]) -> _T:
    """Gets the fallback implementation for `api_type`.

    `api_type` must be a OpenTelemetry API type like `Tracer`.

    First, the function tries to find a module that provides a `get_opentelemetry_backend_impl`
    function (with the same signature as this function). The following modules are tried:

    1. `$OPENTELEMETRY_PYTHON_BACKEND_<typename>` (e.g. `OPENTELEMETRY_PYTHON_BACKEND_TRACER`)
    2. `$OPENTELEMETRY_PYTHON_BACKEND_DEFAULT` (e.g. `OPENTELEMETRY_PYTHON_BACKEND_TRACER`)
    3. The OpenTelemetry SDK's tracer module.

    Note that if any of the environment variables is set to an nonempty value, further steps
    are not tried, even if the modulename set there is invalid or fails to load. The no-op API
    implementation is returned instead.
    """
    backend_modname = None
    if not _UNIT_TEST_IGNORE_ENV and not sys.flags.ignore_environment:
        backend_modname = os.getenv('OPENTELEMETRY_PYTHON_BACKEND_' + api_type.__name__.upper())
        breakpoint()
        if not backend_modname:
            backend_modname = os.getenv('OPENTELEMETRY_PYTHON_BACKEND_DEFAULT')
    if not backend_modname:
        backend_modname = _DEFAULT_BACKEND_MODNAME
    try:
        backend_mod = importlib.import_module(backend_modname)
    except (ImportError, SyntaxError):
        # TODO Log/warn
        return api_type()
    try:
        # Note: We use such a long name to avoid called 
        backend_fn: Callable[[Type[_T]], object] = getattr(backend_mod, 'get_opentelemetry_backend_impl')
    except AttributeError:
        # TODO Log/warn
        return api_type()
    result = backend_fn(api_type)
    if result and isinstance(result, api_type):
        # TODO: Warn if backend_fn returns api_type(): It should return None to indicate using the
        # default.
        return result
    return api_type()

_GETTER_TPL = '''
def make_getter(obj=obj):
    @wraps(original_func)
    def dyn_{getter_name}() -> api_type: return obj

    return dyn_{getter_name}
'''

def _set_backend_object(api_type: Type[_T], obj: _T) -> None:
    """Set the backend object by compiling a function that returns it without accessing a global for
    maximum performance."""

    if not isinstance(obj, api_type):
        raise ValueError('obj is not an instance of api_type. obj\'s type: ' + str(api_type))

    # Note: At some time, instead of lower(), we might need to convert to snake_case here.
    getter_name = api_type.__name__.lower()

    getter_src = _GETTER_TPL.format(getter_name=getter_name)
    getter_code = compile(getter_src, '<generated getter for {}>'.format(api_type.__name__), 'exec')
    original_func = globals()[getter_name]
    if hasattr(original_func, '__wraps__'):
        original_func = original_func.__wraps__
    assert not hasattr(original_func, '__wraps__')
    scope = dict(
        api_type=api_type,
        wraps=wraps,
        original_func=original_func,
        obj=obj)
    exec(getter_code, scope) #pylint:disable=exec-used
    globals()[getter_name] = scope['make_getter']()


def _selectimpl(api_type: Type[_T]) -> _T:
    impl = _get_fallback_impl(api_type)
    assert impl
    _set_backend_object(api_type, impl)
    return impl


### Public code (basically copy & paste for each type) {{{1

def tracer() -> Tracer:
    return _selectimpl(Tracer)

def set_tracer(tracer_implementation: Tracer) -> None:
    _set_backend_object(Tracer, tracer_implementation)
