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
The OpenTelemetry backend module provides access to a selected implementation (backend) of the
OpenTelemetry API.

By default, if you call a getter function (e.g., :func:`tracer`) and the corresponding setter (e.g.,
:func:`set_tracer`) wasn't called, you will get a default implementation, which is selected as
follows:

    1. If the environment variable :samp:`OPENTELEMETRY_PYTHON_BACKEND_{getter-name}` (e.g.,
       ``OPENTELEMETRY_PYTHON_BACKEND_TRACER``) is set to an nonempty value, an attempt is made to
       import a module with that name and call a function ``get_opentelemetry_backend_impl`` in it.
       The function receives the API type that is expected as an argument and should return an
       instance of it (e.g., the argument is :class:`opentelemetry.trace.Tracer` and the function
       should return an instance of a :class:`~opentelemetry.trace.Tracer` (probably of a derived
       type).
    2. If that variable is not set, ``OPENTELEMETRY_PYTHON_BACKEND_DEFAULT`` is tried instead.
    3. If that variable was also not set, an attempt is made to import and use the OpenTelemetry
       SDK.
    4. Otherwise (if no variable was set and the SDK was not importable, or an error occured when
       trying to instantiate the implementation object) the default implementation that ships with
       the API distribution (a fast no-op implementation) is used.

If you called the setter for an object before initializing it that search is not performed and
instead the object you set is used instead. It is also possible to call the setter later to override
the set tracer but this is not recommended.
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
    # TODO: Move (most of) this to module docstring.
    """Gets the fallback implementation for ``api_type``.

    ``api_type`` must be a OpenTelemetry API type like :class:`Tracer`.

    First, the function tries to find a module that provides a `get_opentelemetry_backend_impl`
    function (with the same signature as this function). The following modules are tried:

    1. ``$OPENTELEMETRY_PYTHON_BACKEND_<typename>`` (e.g. ``OPENTELEMETRY_PYTHON_BACKEND_TRACER`)
    2. ``$OPENTELEMETRY_PYTHON_BACKEND_DEFAULT`` (e.g. ``OPENTELEMETRY_PYTHON_BACKEND_TRACER`)
    3. The OpenTelemetry SDK's tracer module.

    Note that if any of the environment variables is set to an nonempty value, further steps
    are not tried, even if the modulename set there is invalid or fails to load. The no-op API
    implementation is returned instead.
    """
    backend_modname = None
    if not _UNIT_TEST_IGNORE_ENV and not sys.flags.ignore_environment:
        backend_modname = os.getenv('OPENTELEMETRY_PYTHON_BACKEND_' + api_type.__name__.upper())
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
        # Note: We use such a long name to avoid calling a function that is not intended for this
        # API.
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

def _selectimpl(api_type: Type[_T]) -> _T:
    impl = _get_fallback_impl(api_type)
    assert impl
    globals()[api_type.__name__.lower()] = impl
    return impl

def _set_backend_object(api_type: Type[_T], impl_object: _T) -> None:
    if impl_object is None:
        raise ValueError('None is not allowed as a backend implementation.')
    if not isinstance(impl_object, api_type):
        raise ValueError('The object does not implement the required base class.')
    globals()['_' + api_type.__name__.lower()] = impl_object

### Public code (basically copy & paste for each type) {{{1

def tracer() -> Tracer:
    """Gets the current global :class:`~opentelemetry.trace.Tracer` object.

    If there isn't one set yet, a default will be used (see module documentation).
    """

    if _tracer:
        return _tracer
    return _selectimpl(Tracer)

def set_tracer(tracer_implementation: Tracer) -> None:
    """Sets the global :class:`~opentelemetry.trace.Tracer` object.

    Args:
        tracer_implementation: The tracer object that should be returned by further calls to
            :func:`tracer`.
    """

    _set_backend_object(Tracer, tracer_implementation)
