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
The OpenTelemetry loader module is mainly used internally to load the
implementation for global objects like :func:`opentelemetry.trace.tracer`.

By default, if you call a getter function (e.g., :func:`tracer`) and the
corresponding setter (e.g., :func:`set_tracer`) wasn't called, you will get a
default implementation, which is selected as follows:

    1. If the environment variable
       :samp:`OPENTELEMETRY_PYTHON_IMPLEMENTATION_{getter-name}` (e.g.,
       ``OPENTELEMETRY_PYTHON_IMPLEMENTATION_TRACER``) is set to an nonempty
       value, an attempt is made to import a module with that name and call a
       function ``get_opentelemetry_implementation`` in it.  The function
       receives the API type that is expected as an argument and should return
       an instance of it (e.g., the argument is
       :class:`opentelemetry.trace.Tracer` and the function should return an
       instance of a :class:`~opentelemetry.trace.Tracer` (probably of a
       derived type).
    2. Otherwise, ``OPENTELEMETRY_PYTHON_IMPLEMENTATION_DEFAULT`` is tried
       instead.
    3. Otherwise, if a :samp:`set_preferred_{<type>}_implementation` was
       called, the module set there is used.
    4. Otherwise, if :func:`set_preferred_default_implementation` was called,
       the module set there is used.
    5. Otherwise, an attempt is made to import and use the OpenTelemetry SDK.
    6. Otherwise the default implementation that ships with the API
       distribution (a fast no-op implementation) is used.

If any of the above steps fails (e.g., a module is loaded but does not define
the required function or a module name is set but the module fails to load),
the search immediatelly skips to the last step.
"""

from typing import Type, TypeVar, Optional, Callable, Dict
import importlib
import os
import sys

_T = TypeVar('_T')

_UntrustedImplFactory = Callable[[Type[_T]], object]

#ImplementationFactory = Callable[[Type[_T]], _T]

_DEFAULT_IMPLEMENTATION_MODNAME = (
    'opentelemetry.sdk.internal.implementation_impl')

_CALLBACKS_BY_TYPE: Dict[Optional[type], _UntrustedImplFactory] = dict()

def _try_load_impl_from_modname(
        implementation_modname: str, api_type: Type[_T]) -> Optional[_T]:
    try:
        implementation_mod = importlib.import_module(implementation_modname)
    except (ImportError, SyntaxError):
        # TODO Log/warn
        return None

    return _try_load_impl_from_mod(implementation_mod, api_type)

def _try_load_impl_from_mod(
        implementation_mod: object, api_type: Type[_T]) -> Optional[_T]:

    try:
        # Note: We use such a long name to avoid calling a function that is not
        # intended for this API.

        implementation_fn = getattr(
            implementation_mod,
            'get_opentelemetry_implementation') # type: _UntrustedImplFactory
    except AttributeError:
        # TODO Log/warn
        return None

    return _try_load_impl_from_callback(implementation_fn, api_type)

def _try_load_impl_from_callback(
        implementation_fn: _UntrustedImplFactory,
        api_type: Type[_T]
        ) -> Optional[_T]:
    result = implementation_fn(api_type)
    if result is None:
        return None
    if not isinstance(result, api_type):
        # TODO Warn if wrong type is returned
        return None

    # TODO: Warn if implementation_fn returns api_type(): It should return None
    # to indicate using the default.

    return result


def _try_load_configured_impl(api_type: Type[_T]) -> Optional[_T]:
    """Attempts to find any specially configured implementation. If none is
    configured, or a load error occurs, returns `None`
    """

    implementation_modname = None
    if sys.flags.ignore_environment:
        return None
    implementation_modname = os.getenv(
        'OPENTELEMETRY_PYTHON_IMPLEMENTATION_' + api_type.__name__.upper())
    if implementation_modname:
        return _try_load_impl_from_modname(implementation_modname, api_type)
    implementation_modname = os.getenv(
        'OPENTELEMETRY_PYTHON_IMPLEMENTATION_DEFAULT')
    if implementation_modname:
        return _try_load_impl_from_modname(implementation_modname, api_type)
    callback = _CALLBACKS_BY_TYPE.get(api_type)
    if callback is not None:
        return _try_load_impl_from_callback(callback, api_type)
    callback = _CALLBACKS_BY_TYPE.get(None)
    if callback is not None:
        return _try_load_impl_from_callback(callback, api_type)
    return None

 # Public to other opentelemetry-api modules
def _load_default_impl(api_type: Type[_T]) -> _T:
    """Tries to load a configured implementation, if unsuccessful, returns a
    fast no-op implemenation that is always available.
    """

    result = _try_load_configured_impl(api_type)
    if result is None:
        return api_type()
    return result

def set_preferred_default_implementation(
        implementation_module: _UntrustedImplFactory) -> None:
    """Sets a module that may be queried for a default implementation. See the
    module docs for more details."""
    _CALLBACKS_BY_TYPE[None] = implementation_module
