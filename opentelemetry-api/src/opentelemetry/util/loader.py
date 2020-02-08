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
implementation for global objects like
:func:`opentelemetry.trace.tracer_source`.

.. _loader-factory:

An instance of a global object of type ``T`` is always created with a factory
function with the following signature::

    def my_factory_for_t(api_type: typing.Type[T]) -> typing.Optional[T]:
        # ...

That function is called with e.g., the type of the global object it should
create as an argument (e.g. the type object
:class:`opentelemetry.trace.TracerSource`) and should return an instance of that type
(such that ``instanceof(my_factory_for_t(T), T)`` is true). Alternatively, it
may return ``None`` to indicate that the no-op default should be used.

When loading an implementation, the following algorithm is used to find a
factory function or other means to create the global object:

    1. If the environment variable
       :samp:`OPENTELEMETRY_PYTHON_IMPLEMENTATION_{getter-name}` (e.g.,
       ``OPENTELEMETRY_PYTHON_IMPLEMENTATION_TRACERSOURCE``) is set to an
       nonempty value, an attempt is made to import a module with that name and
       use a factory function named ``get_opentelemetry_implementation`` in it.
    2. Otherwise, the same is tried with the environment variable
       ``OPENTELEMETRY_PYTHON_IMPLEMENTATION_DEFAULT``.
    3. Otherwise, if a :samp:`set_preferred_{<type>}_implementation` was
       called (e.g.
       :func:`opentelemetry.trace.set_preferred_tracer_source_implementation`),
       the callback set there is used (that is, the environment variables
       override the callback set in code).
    4. Otherwise, if :func:`set_preferred_default_implementation` was called,
       the callback set there is used.
    5. Otherwise, an attempt is made to import and use the OpenTelemetry SDK.
    6. Otherwise the default implementation that ships with the API
       distribution (a fast no-op implementation) is used.

If any of the above steps fails (e.g., a module is loaded but does not define
the required function or a module name is set but the module fails to load),
the search immediatelly skips to the last step.

Note that the first two steps (those that query environment variables) are
skipped if :data:`sys.flags` has ``ignore_environment`` set (which usually
means that the Python interpreter was invoked with the ``-E`` or ``-I`` flag).
"""

import importlib
import os
import sys
from typing import Callable, Optional, Type, TypeVar

_T = TypeVar("_T")

# "Untrusted" because this is usually user-provided and we don't trust the user
# to really return a _T: by using object, mypy forces us to check/cast
# explicitly.
_UntrustedImplFactory = Callable[[Type[_T]], Optional[object]]


# This would be the normal ImplementationFactory which would be used to
# annotate setters, were it not for https://github.com/python/mypy/issues/7092
# Once that bug is resolved, setters should use this instead of duplicating the
# code.
# ImplementationFactory = Callable[[Type[_T]], Optional[_T]]

_DEFAULT_FACTORY = None  # type: Optional[_UntrustedImplFactory[object]]


def _try_load_impl_from_modname(
    implementation_modname: str, api_type: Type[_T]
) -> Optional[_T]:
    try:
        implementation_mod = importlib.import_module(implementation_modname)
    except (ImportError, SyntaxError):
        # TODO Log/warn
        return None

    return _try_load_impl_from_mod(implementation_mod, api_type)


def _try_load_impl_from_mod(
    implementation_mod: object, api_type: Type[_T]
) -> Optional[_T]:

    try:
        # Note: We use such a long name to avoid calling a function that is not
        # intended for this API.

        implementation_fn = getattr(
            implementation_mod, "get_opentelemetry_implementation"
        )  # type: _UntrustedImplFactory[_T]
    except AttributeError:
        # TODO Log/warn
        return None

    return _try_load_impl_from_callback(implementation_fn, api_type)


def _try_load_impl_from_callback(
    implementation_fn: _UntrustedImplFactory[_T], api_type: Type[_T]
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


def _try_load_configured_impl(
    api_type: Type[_T], factory: Optional[_UntrustedImplFactory[_T]]
) -> Optional[_T]:
    """Attempts to find any specially configured implementation. If none is
    configured, or a load error occurs, returns `None`
    """
    implementation_modname = None
    if not sys.flags.ignore_environment:
        implementation_modname = os.getenv(
            "OPENTELEMETRY_PYTHON_IMPLEMENTATION_" + api_type.__name__.upper()
        )
        if implementation_modname:
            return _try_load_impl_from_modname(
                implementation_modname, api_type
            )
        implementation_modname = os.getenv(
            "OPENTELEMETRY_PYTHON_IMPLEMENTATION_DEFAULT"
        )
        if implementation_modname:
            return _try_load_impl_from_modname(
                implementation_modname, api_type
            )
    if factory is not None:
        return _try_load_impl_from_callback(factory, api_type)
    if _DEFAULT_FACTORY is not None:
        return _try_load_impl_from_callback(_DEFAULT_FACTORY, api_type)
    return None


# Public to other opentelemetry-api modules
def _load_impl(
    api_type: Type[_T], factory: Optional[Callable[[Type[_T]], Optional[_T]]]
) -> _T:
    """Tries to load a configured implementation, if unsuccessful, returns a
    fast no-op implemenation that is always available.
    """

    result = _try_load_configured_impl(api_type, factory)
    if result is None:
        return api_type()
    return result


def set_preferred_default_implementation(
    implementation_factory: _UntrustedImplFactory[_T],
) -> None:
    """Sets a factory function that may be called for any implementation
    object. See the :ref:`module docs <loader-factory>` for more details."""
    global _DEFAULT_FACTORY  # pylint:disable=global-statement
    _DEFAULT_FACTORY = implementation_factory
