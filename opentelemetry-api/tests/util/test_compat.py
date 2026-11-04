# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pyright: reportIncompatibleMethodOverride=false
# pylint: disable=arguments-differ,unexpected-keyword-arg,missing-kwoa,no-self-use,too-many-public-methods,too-many-function-args

import sys
import unittest
from abc import abstractmethod
from collections.abc import Callable
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

    def test_partial_evolution_subclass_forwards_supported_subset(self) -> None:
        class PartialGreeter(BaseGreeter):
            # Supports `name` and `time`, but predates `locale`
            def say_hello(self, *, name: str, time: datetime | None = None) -> str:
                suffix = f" at {time.isoformat()}" if time else ""
                return f"Hello {name}{suffix}"

        greeter = _as_base_greeter(PartialGreeter())
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.assertEqual(
            greeter.say_hello(name="Alice", time=ts, locale="de"),
            "Hello Alice at 2026-01-01T00:00:00+00:00",
        )

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

    def test_override_named_like_a_lambda_is_wrapped(self) -> None:
        def impl(self: object, *, name: str) -> str:
            return f"Hello {name}"

        # Not a valid identifier, like any lambda's __name__
        impl.__name__ = "<lambda>"

        class LambdaGreeter(BaseGreeter):
            say_hello = cast(Callable[..., str], impl)

        self.assertTrue(hasattr(LambdaGreeter.say_hello, "__wrapped__"))
        self.assertEqual(_as_base_greeter(LambdaGreeter()).say_hello(name="Alice", locale="fr"), "Hello Alice")

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

    def test_positional_only_and_varargs_parameters_supported(self) -> None:
        def sub_fn(self: object, x: int, /, y: int, *args: int, z: int = 0) -> int:
            return x + y + sum(args) + z

        wrapped = make_signature_compat_wrapper(sub_fn)
        self.assertIsNotNone(wrapped)
        assert wrapped is not None
        self.assertEqual(wrapped(object(), 2, 3, 4, 5, z=10, extra="ignored"), 24)
        self.assertEqual(wrapped(object(), 2, 10, extra="ignored"), 12)
        with self.assertRaises(TypeError):
            # x is positional-only, so passing x as a keyword argument fails
            wrapped(object(), x=2, y=3, z=10)

    def test_parameter_names_do_not_collide_with_generated_names(self) -> None:
        # Parameter names that match the identifiers used inside the generated
        # wrapper source must not shadow them.
        def sub_fn(_sub_fn: object, _sub_fn_: str, _compat_fn: int = 2) -> str:
            return f"{_sub_fn_}:{_compat_fn}"

        wrapped = make_signature_compat_wrapper(sub_fn)
        self.assertIsNotNone(wrapped)
        assert wrapped is not None
        self.assertEqual(wrapped(object(), "a", extra="ignored"), "a:2")
        self.assertEqual(wrapped(object(), "a", _compat_fn=4, extra="ignored"), "a:4")

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
