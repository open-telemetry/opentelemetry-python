# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import functools
import inspect
import logging
import sys
from abc import ABC
from collections.abc import Callable, Mapping
from inspect import Parameter, Signature
from typing import Any

_logger = logging.getLogger(__name__)

if sys.version_info >= (3, 14):
    from annotationlib import Format


def _signature(fn: Callable[..., Any]) -> inspect.Signature:
    if sys.version_info >= (3, 14):
        # PEP 649: inspect.signature() evaluates deferred annotations by
        # default, which raises NameError for names that only exist under
        # TYPE_CHECKING. Only parameter names, kinds and defaults are needed.
        return inspect.signature(fn, annotation_format=Format.FORWARDREF)  # pylint: disable=unexpected-keyword-arg
    return inspect.signature(fn)


def _unused_name(base: str, taken: Mapping[str, Any]) -> str:
    """Return ``base``, suffixed with underscores until it is not a key of ``taken``."""
    name = base
    while name in taken:
        name += "_"
    return name


def make_signature_compat_wrapper(
    sub_fn: Callable[..., Any],
    *,
    qualname: str | None = None,
) -> Callable[..., Any] | None:
    """Wrap ``sub_fn`` so that it also accepts, and ignores, unknown keyword arguments.

    The wrapper has ``sub_fn``'s signature plus a trailing ``**_kwargs``. It passes
    arguments to ``sub_fn`` by name rather than through ``*args``/``**kwargs``,
    which keeps the forwarding call cheap.

    Returns ``None`` if ``sub_fn`` already accepts ``**kwargs``.
    """
    parameters = _signature(sub_fn).parameters
    if any(param.kind is Parameter.VAR_KEYWORD for param in parameters.values()):
        return None

    # Let inspect.Signature render the ``def`` line (including ``/`` and ``*``
    # markers). Annotations are dropped and defaults are attached afterwards via
    # __defaults__/__kwdefaults__ so no values need to be in the source.
    definition = Signature(
        [param.replace(annotation=Parameter.empty, default=Parameter.empty) for param in parameters.values()]
        + [Parameter("_kwargs", Parameter.VAR_KEYWORD)]
    )
    call_parts: list[str] = []
    positional_defaults: list[Any] = []
    keyword_defaults: dict[str, Any] = {}
    for name, param in parameters.items():
        if param.kind is Parameter.VAR_POSITIONAL:
            call_parts.append(f"*{name}")
        elif param.kind is Parameter.KEYWORD_ONLY:
            call_parts.append(f"{name}={name}")
            if param.default is not Parameter.empty:
                keyword_defaults[name] = param.default
        else:
            call_parts.append(name)
            if param.default is not Parameter.empty:
                positional_defaults.append(param.default)

    # The generated function's own parameters shadow the closed-over name, so the
    # reference to ``sub_fn`` must not collide with any of its parameter names.
    sub_fn_name = _unused_name("_sub_fn", parameters)
    target_qualname = qualname or getattr(sub_fn, "__qualname__", "_compat_fn")
    src = (
        f"def __create_compat_fn__({sub_fn_name}):\n"
        f"    def _compat_fn{definition}:\n"
        f"        return {sub_fn_name}({', '.join(call_parts)})\n"
        f"    return _compat_fn\n"
    )
    namespace: dict[str, Any] = {}
    exec(compile(src, f"<compat {target_qualname}>", "exec"), {"__builtins__": {}}, namespace)  # noqa: S102  # pylint: disable=exec-used
    wrapper: Callable[..., Any] = namespace["__create_compat_fn__"](sub_fn)
    wrapper.__defaults__ = tuple(positional_defaults) or None
    wrapper.__kwdefaults__ = keyword_defaults or None
    functools.update_wrapper(wrapper, sub_fn)
    return wrapper


def _overrides_api_method(cls: type, name: str, fn: object) -> bool:
    """Whether ``fn``, defined on ``cls`` as ``name``, implements a public API method."""
    if name.startswith("_") or not inspect.isfunction(fn) or getattr(fn, "__isabstractmethod__", False):
        return False
    return any(
        base is not SignatureCompatABC
        and issubclass(base, SignatureCompatABC)
        and inspect.isfunction(base.__dict__.get(name))
        for base in cls.__mro__[1:]
    )


class SignatureCompatABC(ABC):
    """ABC base class that keeps subclass method signatures forward-compatible.

    When a subclass implements a public method of the base without accepting
    ``**kwargs``, the method is replaced on the subclass with a generated wrapper
    that accepts ``sub_fn``'s exact signature plus ``**_kwargs`` and forwards the
    declared parameters directly. Subclasses that accept ``**kwargs`` are left
    untouched.

    Only unknown *keyword* arguments are absorbed, so new optional parameters on
    API methods must be keyword-only, have a default and be safe for an
    implementation to ignore. New positional parameters and new abstract methods
    still break existing implementations.

    The signature is read with :func:`inspect.signature`, which follows
    ``__wrapped__``. Decorators applied to overriding methods must therefore use
    :func:`functools.wraps`; a bare ``def wrapper(self, *args, **kwargs)`` makes
    the method look like it already accepts ``**kwargs`` and it is left unwrapped.
    Conversely, extra keyword arguments that only a decorator accepts are not
    visible through ``__wrapped__`` and are dropped by the generated wrapper.
    Overrides that are not plain functions (for example ``functools.lru_cache``
    objects or methods implemented in C) are not adapted.
    """

    # TODO(#5877): The SDK's methods don't accept **kwargs yet, so they are wrapped
    # too (a small per-call cost) even though the SDK pins the same API version.

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        for name, sub_fn in list(vars(cls).items()):
            qualname = f"{cls.__qualname__}.{name}"
            try:
                if not _overrides_api_method(cls, name, sub_fn):
                    continue
                wrapper = make_signature_compat_wrapper(sub_fn, qualname=qualname)
                if wrapper is not None:
                    setattr(cls, name, wrapper)
            except Exception:  # pylint: disable=broad-exception-caught
                # Best effort: never let the shim itself break defining a subclass.
                _logger.debug("Not adapting %s", qualname, exc_info=True)
