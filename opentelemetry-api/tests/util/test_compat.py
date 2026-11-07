# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pyright: reportIncompatibleMethodOverride=false
# pylint: disable=arguments-differ,unexpected-keyword-arg,missing-kwoa,no-self-use,too-many-public-methods,too-many-function-args

import linecache
import sys
import textwrap
import unittest
from abc import abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, cast

from opentelemetry.util._compat import (
    SignatureCompatABC,
    make_signature_compat_wrapper,
)

if TYPE_CHECKING:
    # Exists only for type checkers; evaluating it at runtime raises NameError.
    TypeCheckingOnlyStr = str


class BaseGreeter(SignatureCompatABC):
    @abstractmethod
    def say_hello(
        self,
        *,
        name: str,
        time: datetime | None = None,
        locale: str = "en",
    ) -> str:
        pass

    def format_prefix(self, greeting: str, repeat: int = 1, *, punctuation: str = "!") -> str:
        return f"{greeting * repeat}{punctuation}"


def _as_base_greeter(greeter: BaseGreeter) -> BaseGreeter:
    return greeter


def _dynamic(fn: Callable[..., Any]) -> Callable[..., Any]:
    return fn


class TestSignatureCompatABC(unittest.TestCase):
    def test_subclass_without_kwargs_is_wrapped(self) -> None:
        class LegacyGreeter(BaseGreeter):
            def say_hello(self, *, name: str) -> str:
                return f"Hello {name}"

        greeter = _as_base_greeter(LegacyGreeter())
        now = datetime.now(timezone.utc)

        # Callers can pass new optional keyword arguments without TypeError
        self.assertEqual(greeter.say_hello(name="Alice", time=now), "Hello Alice")
        self.assertEqual(greeter.say_hello(name="Alice", time=now, locale="fr"), "Hello Alice")
        # Future unknown keyword arguments are also accepted without TypeError
        self.assertEqual(_dynamic(greeter.say_hello)(name="Alice", future_opt=123), "Hello Alice")
        # Old callers omitting the new parameters continue to work
        self.assertEqual(greeter.say_hello(name="Bob"), "Hello Bob")

        self.assertTrue(hasattr(LegacyGreeter.say_hello, "__wrapped__"))

    def test_kwargs_subclass_is_not_wrapped(self) -> None:
        def impl_kwargs(self: object, *, name: str, **kwargs: object) -> str:
            return f"Hello {name} ({len(kwargs)} extras)"

        class KwargsGreeter(BaseGreeter):
            say_hello = impl_kwargs

        # Exact same function object on the class: no wrapper frame added
        self.assertIs(KwargsGreeter.__dict__["say_hello"], impl_kwargs)
        self.assertEqual(
            KwargsGreeter().say_hello(name="Alice", time=None, locale="es"),
            "Hello Alice (2 extras)",
        )

    def test_missing_required_and_excess_positional_args_still_raise_type_error(self) -> None:
        class LegacyGreeter(BaseGreeter):
            def say_hello(self, *, name: str) -> str:
                return f"Hello {name}"

            def format_prefix(self, greeting: str) -> str:
                return f"[{greeting}]"

        greeter = _as_base_greeter(LegacyGreeter())

        # Missing required keyword-only argument must still raise TypeError
        with self.assertRaises(TypeError):
            _dynamic(greeter.say_hello)()

        # Excess positional arguments must still raise TypeError
        with self.assertRaises(TypeError):
            greeter.format_prefix("Hi", 2)

    def test_multilevel_inheritance_super_calls(self) -> None:
        class LegacyParent(BaseGreeter):
            def say_hello(self, *, name: str) -> str:
                return f"Parent:{name}"

            def format_prefix(self, greeting: str) -> str:
                return f"[{greeting}]"

        class ModernChild(LegacyParent):
            def say_hello(
                self,
                *,
                name: str,
                time: datetime | None = None,
                locale: str = "en",
                **kwargs: Any,
            ) -> str:
                # Calling super() with the new arguments works even though
                # LegacyParent only implemented the old signature
                super_say_hello = _dynamic(super().say_hello)
                base_res = super_say_hello(name=name, time=time, locale=locale, **kwargs)
                return f"{base_res}:{locale}"

        child = _as_base_greeter(ModernChild())
        self.assertEqual(child.say_hello(name="Alice", time=None, locale="jp"), "Parent:Alice:jp")
        # The override with **kwargs is not wrapped; the inherited legacy method stays wrapped once
        self.assertFalse(hasattr(ModernChild.say_hello, "__wrapped__"))
        self.assertIs(ModernChild.format_prefix, LegacyParent.format_prefix)
        self.assertEqual(child.format_prefix("Hi", punctuation="?!"), "[Hi]")

    def test_generated_source(self) -> None:
        @dataclass
        class Case:
            fn: Callable[..., Any]
            source: str
            call: Callable[[Callable[..., Any]], Any]
            result: Any

        def plain(self: object, name: str, context: object = None, *, kind: int = 0) -> tuple[Any, ...]:
            return (name, context, kind)

        def positional_only_and_varargs(self: object, x: int, /, y: int, *args: int, z: int = 0) -> tuple[Any, ...]:
            return (x, y, args, z)

        def parameters_named_like_generated_names(_fn: object, _fn_: str, _compat_fn: int = 2) -> tuple[Any, ...]:
            return (_fn_, _compat_fn)

        def keyword_only_with_default(self: object, *, name: str = "x") -> tuple[Any, ...]:
            return (name,)

        # Expected sources have no annotations or defaults: the wrapper gets its
        # defaults from __defaults__/__kwdefaults__ instead, asserted below.
        cases = [
            Case(
                fn=plain,
                source="""\
                def _compat_fn(self, name, context, *, kind, **_kwargs):
                    return _fn(self, name, context, kind=kind)
                """,
                call=lambda wrapped: wrapped(object(), "n", kind=3, not_yet_invented=True),
                result=("n", None, 3),
            ),
            Case(
                fn=positional_only_and_varargs,
                source="""\
                def _compat_fn(self, x, /, y, *args, z, **_kwargs):
                    return _fn(self, x, y, *args, z=z)
                """,
                call=lambda wrapped: wrapped(object(), 1, 2, 3, 4, z=5, not_yet_invented=True),
                result=(1, 2, (3, 4), 5),
            ),
            Case(
                fn=parameters_named_like_generated_names,
                source="""\
                def _compat_fn(_fn, _fn_, _compat_fn, **_kwargs):
                    return _fn__(_fn, _fn_, _compat_fn)
                """,
                call=lambda wrapped: wrapped(object(), _fn_="a", _compat_fn=4, not_yet_invented=True),
                result=("a", 4),
            ),
            Case(
                fn=keyword_only_with_default,
                source="""\
                def _compat_fn(self, *, name, **_kwargs):
                    return _fn(self, name=name)
                """,
                call=lambda wrapped: wrapped(object(), not_yet_invented=True),
                result=("x",),
            ),
        ]
        for case in cases:
            with self.subTest(case.fn.__name__):
                wrapped = make_signature_compat_wrapper(case.fn)
                assert wrapped is not None
                source = "".join(linecache.getlines(wrapped.__code__.co_filename))
                self.assertEqual(source, textwrap.dedent(case.source))
                self.assertEqual(wrapped.__defaults__, case.fn.__defaults__)
                self.assertEqual(wrapped.__kwdefaults__, case.fn.__kwdefaults__)
                self.assertEqual(case.call(wrapped), case.result)

    def test_unadaptable_override_does_not_break_class_definition(self) -> None:
        def impl(self: object, *, name: str) -> str:
            return f"Hello {name}"

        # inspect.signature() rejects this and raises TypeError
        impl.__signature__ = "not a signature"  # pyright: ignore[reportFunctionMemberAccess]

        with self.assertLogs("opentelemetry.util._compat", level="DEBUG") as logs:

            class BrokenGreeter(BaseGreeter):
                say_hello = cast(Callable[..., str], impl)

        self.assertIs(BrokenGreeter.__dict__["say_hello"], impl)
        self.assertEqual(BrokenGreeter().say_hello(name="Bob"), "Hello Bob")
        self.assertIn("Not adapting", logs.output[0])
        self.assertIn("BrokenGreeter.say_hello", logs.output[0])

    @unittest.skipIf(sys.version_info < (3, 14), "requires PEP 649 deferred annotations")
    def test_annotations_are_not_evaluated(self) -> None:
        class AnnotatedGreeter(BaseGreeter):
            def say_hello(self, *, name: TypeCheckingOnlyStr) -> str:  # pylint: disable=used-before-assignment
                return name

        self.assertTrue(hasattr(AnnotatedGreeter.say_hello, "__wrapped__"))
        self.assertEqual(_as_base_greeter(AnnotatedGreeter()).say_hello(name="Bob", locale="fr"), "Bob")
