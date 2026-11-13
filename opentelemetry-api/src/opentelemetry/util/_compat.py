# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import functools
import inspect
import linecache
import logging
import sys
import textwrap
from abc import ABC
from collections.abc import Callable
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


def make_signature_compat_wrapper(fn: Callable[..., Any]) -> Callable[..., Any] | None:
    """Wrap ``fn`` so that it also accepts, and ignores, unknown keyword arguments.

    The wrapper has ``fn``'s signature plus a trailing ``**_kwargs``. It forwards
    each declared parameter individually rather than through ``*args``/``**kwargs``,
    which keeps the forwarding call cheap.

    Returns ``None`` if ``fn`` already accepts ``**kwargs``.
    """
    parameters = _signature(fn).parameters
    if any(param.kind is Parameter.VAR_KEYWORD for param in parameters.values()):  # already accepts **kwargs
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

    # The generated function's own parameters shadow globals, so the name used to
    # reference ``fn`` must not collide with any of its parameter names.
    fn_name = "_fn"
    while fn_name in parameters:
        fn_name += "_"
    src = textwrap.dedent(f"""\
        def _compat_fn{definition}:
            return {fn_name}({", ".join(call_parts)})
        """)
    filename = f"<compat {fn.__module__}.{fn.__qualname__}>"
    # Make the generated source visible in tracebacks
    linecache.cache[filename] = (len(src), None, src.splitlines(True), filename)
    namespace: dict[str, Any] = {}
    # The only caller-controlled text in ``src`` is parameter names, which
    # inspect.Parameter guarantees are identifiers (defaults and annotations, whose
    # repr would be arbitrary text, were stripped above).
    exec(  # noqa: S102  # pylint: disable=exec-used
        compile(src, filename, "exec"),
        {"__builtins__": {}, fn_name: fn},
        namespace,
    )
    wrapper: Callable[..., Any] = namespace["_compat_fn"]
    wrapper.__defaults__ = tuple(positional_defaults) or None
    wrapper.__kwdefaults__ = keyword_defaults or None
    functools.update_wrapper(wrapper, fn)
    return wrapper


def _is_public_api_method(cls: type, name: str, fn: object) -> bool:
    if name.startswith("_") or not inspect.isfunction(fn):
        return False
    if getattr(fn, "__isabstractmethod__", False):
        # fn is itself an abstract re-declaration (intermediate ABC): nothing to forward to
        return False
    # Some class further up the MRO defines a method with this name
    return any(inspect.isfunction(vars(base).get(name)) for base in cls.__mro__[1:])


class SignatureCompatABC(ABC):
    """ABC base class that keeps subclass method signatures forward-compatible.

    When a subclass implements a public method of the base without accepting
    ``**kwargs``, the method is replaced on the subclass with a generated wrapper
    that accepts the method's exact signature plus ``**_kwargs`` and forwards the
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

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        for name, fn in list(vars(cls).items()):
            try:
                if not _is_public_api_method(cls, name, fn):
                    continue
                wrapper = make_signature_compat_wrapper(fn)
                if wrapper is not None:
                    setattr(cls, name, wrapper)
            except Exception:  # pylint: disable=broad-exception-caught
                # Best effort: never let the shim itself break defining a subclass.
                _logger.debug("Not adapting %s.%s", cls.__qualname__, name, exc_info=True)
