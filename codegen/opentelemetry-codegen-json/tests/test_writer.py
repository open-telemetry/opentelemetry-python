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
from typing import Optional, Any

import pytest
from opentelemetry.codegen.json.writer import CodeWriter


def test_initialization() -> None:
    writer = CodeWriter(indent_size=2)
    assert writer._indent_size == 2
    assert writer.to_lines() == []
    assert writer.to_string() == ""


def test_writeln_indentation() -> None:
    writer = CodeWriter(indent_size=4)
    writer.writeln("line1")
    with writer.indent():
        writer.writeln("line2")
        with writer.indent():
            writer.writeln("line3")
    writer.writeln("line4")

    expected = ["line1", "    line2", "        line3", "line4"]
    assert writer.to_lines() == expected


def test_writemany() -> None:
    writer = CodeWriter()
    writer.writemany("a", "b", "c")
    assert writer.to_lines() == ["a", "b", "c"]


@pytest.mark.parametrize(
    "content, expected",
    [
        ("single line", ["# single line"]),
        (["line1", "line2"], ["# line1", "# line2"]),
    ],
)
def test_comment(content: str, expected: list[str]) -> None:
    writer = CodeWriter()
    writer.comment(content)
    assert writer.to_lines() == expected


@pytest.mark.parametrize(
    "content, expected",
    [
        ("single line", ['"""single line"""']),
        (["line1", "line2"], ['"""', "line1", "line2", '"""']),
    ],
)
def test_docstring(content: str, expected: list[str]) -> None:
    writer = CodeWriter()
    writer.docstring(content)
    assert writer.to_lines() == expected


@pytest.mark.parametrize(
    "module, items, expected",
    [
        ("os", [], ["import os"]),
        ("typing", ["Any", "Optional"], ["from typing import Any, Optional"]),
    ],
)
def test_import(module: str, items: list[str], expected: list[str]) -> None:
    writer = CodeWriter()
    writer.import_(module, *items)
    assert writer.to_lines() == expected


def test_suite() -> None:
    writer = CodeWriter()
    with writer.suite("def foo():"):
        writer.writeln("pass")
    assert writer.to_lines() == ["def foo():", "    pass"]


@pytest.mark.parametrize(
    "name, bases, decorators, expected",
    [
        ("MyClass", None, None, ["class MyClass:"]),
        ("MyClass", ["Base"], ["deco"], ["@deco", "class MyClass(Base):"]),
        (
            "MyClass",
            ["B1", "B2"],
            ["d1", "d2"],
            ["@d1", "@d2", "class MyClass(B1, B2):"],
        ),
    ],
)
def test_class(
    name: str,
    bases: Optional[str],
    decorators: Optional[list[str]],
    expected: list[str],
) -> None:
    writer = CodeWriter()
    with writer.class_(name, bases=bases, decorators=decorators):
        pass
    assert writer.to_lines() == expected


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        ({"name": "DC"}, ["@dataclasses.dataclass", "class DC:"]),
        (
            {"name": "DC", "frozen": True},
            ["@dataclasses.dataclass(frozen=True)", "class DC:"],
        ),
        (
            {"name": "DC", "slots": True},
            ["@dataclasses.dataclass(slots=True)", "class DC:"],
        ),
        (
            {"name": "DC", "frozen": True, "slots": True},
            ["@dataclasses.dataclass(frozen=True, slots=True)", "class DC:"],
        ),
        (
            {"name": "DC", "decorator_name": "custom.dc"},
            ["@custom.dc", "class DC:"],
        ),
    ],
)
def test_dataclass(kwargs: dict[str, Any], expected: list[str]) -> None:
    writer = CodeWriter()
    with writer.dataclass(**kwargs):
        pass
    assert writer.to_lines() == expected


def test_enum() -> None:
    writer = CodeWriter()
    with writer.enum("MyEnum", bases=["IntEnum"]):
        writer.enum_member("A", 1)
        writer.auto_enum_member("B")
    expected = [
        "class MyEnum(enum.Enum, IntEnum):",
        "    A = 1",
        "    B = enum.auto()",
    ]
    assert writer.to_lines() == expected


@pytest.mark.parametrize(
    "name, type_hint, default, default_factory, expected",
    [
        ("x", "int", None, None, ["x: int"]),
        ("x", "int", 10, None, ["x: int = 10"]),
        (
            "x",
            "list",
            None,
            "list",
            ["x: list = dataclasses.field(default_factory=list)"],
        ),
    ],
)
def test_field(
    name: str,
    type_hint: str,
    default: Optional[Any],
    default_factory: Optional[Any],
    expected: list[str],
) -> None:
    writer = CodeWriter()
    writer.field(
        name, type_hint, default=default, default_factory=default_factory
    )
    assert writer.to_lines() == expected


def test_function() -> None:
    writer = CodeWriter()
    with writer.function("foo", ["a: int", "b: str"], return_type="bool"):
        writer.return_("True")
    expected = ["def foo(a: int, b: str) -> bool:", "    return True"]
    assert writer.to_lines() == expected


def test_write_function() -> None:
    writer = CodeWriter()
    writer.write_function("bar", "x", ["return x * 2"], decorators=["deco"])
    expected = ["@deco", "def bar(x):", "    return x * 2"]
    assert writer.to_lines() == expected


def test_special_methods() -> None:
    writer = CodeWriter()
    writer.staticmethod_("s", "x", "pass")
    writer.classmethod_("c", "cls", "pass")
    assert "@builtins.staticmethod" in writer.to_string()
    assert "@builtins.classmethod" in writer.to_string()


def test_control_flow() -> None:
    writer = CodeWriter()
    with writer.if_("a > b"):
        writer.pass_()
    with writer.elif_("a == b"):
        writer.break_()
    with writer.else_():
        writer.continue_()

    expected = [
        "if a > b:",
        "    pass",
        "elif a == b:",
        "    break",
        "else:",
        "    continue",
    ]
    assert writer.to_lines() == expected


def test_loops() -> None:
    writer = CodeWriter()
    with writer.for_("i", "range(10)"):
        writer.writeln("print(i)")
    with writer.while_("True"):
        writer.writeln("break")

    expected = [
        "for i in range(10):",
        "    print(i)",
        "while True:",
        "    break",
    ]
    assert writer.to_lines() == expected


def test_try_except_finally() -> None:
    writer = CodeWriter()
    with writer.try_():
        writer.raise_("ValueError", "oops")
    with writer.except_("ValueError", as_var="e"):
        writer.writeln("print(e)")
    with writer.finally_():
        writer.pass_()

    expected = [
        "try:",
        "    raise ValueError('oops')",
        "except ValueError as e:",
        "    print(e)",
        "finally:",
        "    pass",
    ]
    assert writer.to_lines() == expected


def test_with() -> None:
    writer = CodeWriter()
    with writer.with_("open('f') as f", "open('g') as g"):
        writer.pass_()
    assert writer.to_lines() == [
        "with open('f') as f, open('g') as g:",
        "    pass",
    ]


def test_assignment_and_assertions() -> None:
    writer = CodeWriter()
    writer.assignment("x", "1", type_hint="int")
    writer.assert_("x == 1", "must be 1")
    writer.yield_("x")

    expected = ["x: int = 1", "assert x == 1, 'must be 1'", "yield x"]
    assert writer.to_lines() == expected


def test_generate_init() -> None:
    writer = CodeWriter()
    writer.generate_init({"a": "int", "b": "str"})
    expected = [
        "def __init__(self, a: int, b: str):",
        "    self.a = a",
        "    self.b = b",
    ]
    assert writer.to_lines() == expected


def test_generate_repr() -> None:
    writer = CodeWriter()
    writer.generate_repr("Point", ["x", "y"])
    expected = [
        "def __repr__(self) -> builtins.str:",
        "    return f'Point(x={self.x!r}, y={self.y!r})'",
    ]
    assert writer.to_lines() == expected


def test_generate_eq() -> None:
    writer = CodeWriter()
    writer.generate_eq(["x", "y"])
    expected = [
        "def __eq__(self, other) -> builtins.bool:",
        "    if not isinstance(other, self.__class__):",
        "        return False",
        "    return self.x == other.x and self.y == other.y",
    ]
    assert writer.to_lines() == expected


def test_generate_hash() -> None:
    writer = CodeWriter()
    writer.generate_hash(["x", "y"])
    expected = [
        "def __hash__(self) -> builtins.int:",
        "    return builtins.hash((self.x, self.y))",
    ]
    assert writer.to_lines() == expected


def test_generate_hash_empty() -> None:
    writer = CodeWriter()
    writer.generate_hash([])
    expected = [
        "def __hash__(self) -> builtins.int:",
        "    return builtins.hash(builtins.id(self))",
    ]
    assert writer.to_lines() == expected


def test_write_block() -> None:
    writer = CodeWriter()
    writer.write_block(["line1", "line2"])
    assert writer.to_lines() == ["line1", "line2"]


def test_method_alias():
    writer = CodeWriter()
    with writer.method("m", "self"):
        writer.pass_()
    assert "def m(self):" in writer.to_string()


def test_generate_str() -> None:
    writer = CodeWriter()
    writer.generate_str("Point", ["x", "y"])
    expected = [
        "def __str__(self) -> builtins.str:",
        "    return f'Point(x={self.x}, y={self.y})'",
    ]
    assert writer.to_lines() == expected


def test_formatting_utilities() -> None:
    writer = CodeWriter()
    writer.module_docstring("Module doc")
    writer.section("Title", char="-", width=10)
    writer.blank_line(2)

    output = writer.to_string()
    assert '"""Module doc"""' in output
    assert "# ----------" in output
    assert "#  Title" in output
    assert output.count("\n\n") >= 2
