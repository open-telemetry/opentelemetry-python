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

from __future__ import annotations

from collections.abc import Iterable
from contextlib import contextmanager
from typing import Any, Generator, Mapping, Optional, Union


class CodeWriter:
    def __init__(self, indent_size: int = 4) -> None:
        self._lines: list[str] = []
        self._indent_level: int = 0
        self._indent_size: int = indent_size

    @contextmanager
    def indent(self) -> Generator[CodeWriter, None, None]:
        self._indent_level += 1
        try:
            yield self
        finally:
            self._indent_level -= 1

    def writeln(self, line: str = "") -> CodeWriter:
        if not line:
            self._lines.append("")
            return self
        indent = " " * (self._indent_level * self._indent_size)
        self._lines.append(f"{indent}{line}")
        return self

    def writemany(self, *lines: str) -> CodeWriter:
        for line in lines:
            self.writeln(line)
        return self

    def comment(self, content: Union[str, Iterable[str]]) -> CodeWriter:
        if isinstance(content, str):
            self.writeln(f"# {content}")
            return self
        for line in content:
            self.writeln(f"# {line}")
        return self

    def docstring(self, content: Union[str, Iterable[str]]) -> CodeWriter:
        if isinstance(content, str):
            self.writeln(f'"""{content}"""')
            return self
        self.writeln('"""')
        for line in content:
            self.writeln(line)
        self.writeln('"""')
        return self

    def import_(self, module: str, *items: str) -> CodeWriter:
        if items:
            self.writeln(f"from {module} import {', '.join(items)}")
        else:
            self.writeln(f"import {module}")
        return self

    @contextmanager
    def suite(self, header: str) -> Generator[CodeWriter, None, None]:
        """Write header then indent"""
        self.writeln(header)
        with self.indent():
            yield self

    @contextmanager
    def class_(
        self,
        name: str,
        bases: Optional[Iterable[str]] = None,
        decorators: Optional[Iterable[str]] = None,
    ) -> Generator[CodeWriter, None, None]:
        """Create a regular class with optional bases and decorators"""
        if decorators is not None:
            for dec in decorators:
                self.writeln(f"@{dec}")

        bases_str = f"({', '.join(bases)})" if bases else ""
        self.writeln(f"class {name}{bases_str}:")

        with self.indent():
            yield self

    @contextmanager
    def dataclass(
        self,
        name: str,
        bases: Optional[Iterable[str]] = None,
        decorators: Optional[Iterable[str]] = None,
        frozen: bool = False,
        slots: bool = False,
        decorator_name: str = "dataclasses.dataclass",
    ) -> Generator[CodeWriter, None, None]:
        """Create a dataclass with optional configuration"""
        dc_params = []
        if frozen:
            dc_params.append("frozen=True")
        if slots:
            dc_params.append("slots=True")

        dc_decorator = (
            f"{decorator_name}({', '.join(dc_params)})"
            if dc_params
            else decorator_name
        )

        all_decorators = []
        if decorators is not None:
            all_decorators.extend(decorators)
        all_decorators.append(dc_decorator)

        for dec in all_decorators:
            self.writeln(f"@{dec}")

        bases_str = f"({', '.join(bases)})" if bases else ""
        self.writeln(f"class {name}{bases_str}:")

        with self.indent():
            yield self

    @contextmanager
    def enum(
        self,
        name: str,
        enum_type: str = "enum.Enum",
        bases: Optional[Iterable[str]] = None,
        decorators: Optional[Iterable[str]] = None,
    ) -> Generator[CodeWriter, None, None]:
        """Create an enum"""
        if decorators is not None:
            for dec in decorators:
                self.writeln(f"@{dec}")

        all_bases = [enum_type]
        if bases is not None:
            all_bases.extend(bases)

        bases_str = ", ".join(all_bases)
        self.writeln(f"class {name}({bases_str}):")

        with self.indent():
            yield self

    def field(
        self,
        name: str,
        type_hint: str,
        default: Any = None,
        default_factory: Optional[str] = None,
    ) -> CodeWriter:
        """Write a dataclass field"""
        if default_factory:
            self.writeln(
                f"{name}: {type_hint} = dataclasses.field(default_factory={default_factory})"
            )
        elif default is not None:
            self.writeln(f"{name}: {type_hint} = {default}")
        else:
            self.writeln(f"{name}: {type_hint}")
        return self

    def enum_member(self, name: str, value: Any) -> CodeWriter:
        """Write an enum member"""
        self.writeln(f"{name} = {value}")
        return self

    def auto_enum_member(self, name: str) -> CodeWriter:
        """Write an auto() enum member"""
        self.writeln(f"{name} = enum.auto()")
        return self

    @contextmanager
    def function(
        self,
        name: str,
        params: Union[Iterable[str], str],
        decorators: Optional[Iterable[str]] = None,
        return_type: Optional[str] = None,
    ) -> Generator[CodeWriter, None, None]:
        """Create a function as a context manager for building the body"""
        if decorators is not None:
            for dec in decorators:
                self.writeln(f"@{dec}")

        params_str = params if isinstance(params, str) else ", ".join(params)
        return_annotation = f" -> {return_type}" if return_type else ""
        self.writeln(f"def {name}({params_str}){return_annotation}:")

        with self.indent():
            yield self

    def write_function(
        self,
        name: str,
        params: Union[Iterable[str], str],
        body_lines: Union[Iterable[str], str],
        decorators: Optional[Iterable[str]] = None,
        return_type: Optional[str] = None,
    ) -> CodeWriter:
        """Write a complete function"""
        with self.function(
            name, params, decorators=decorators, return_type=return_type
        ):
            if isinstance(body_lines, str):
                self.writeln(body_lines)
            else:
                for line in body_lines:
                    self.writeln(line)
        return self

    @contextmanager
    def method(
        self,
        name: str,
        params: Union[Iterable[str], str],
        decorators: Optional[Iterable[str]] = None,
        return_type: Optional[str] = None,
    ) -> Generator[CodeWriter, None, None]:
        """Alias for function() - more semantic for methods in classes"""
        with self.function(
            name, params, decorators=decorators, return_type=return_type
        ):
            yield self

    def staticmethod_(
        self,
        name: str,
        params: Union[Iterable[str], str],
        body_lines: Union[Iterable[str], str],
        return_type: Optional[str] = None,
    ) -> CodeWriter:
        return self.write_function(
            name,
            params,
            body_lines,
            decorators=["builtins.staticmethod"],
            return_type=return_type,
        )

    def classmethod_(
        self,
        name: str,
        params: Union[Iterable[str], str],
        body_lines: Union[Iterable[str], str],
        return_type: Optional[str] = None,
    ) -> CodeWriter:
        return self.write_function(
            name,
            params,
            body_lines,
            decorators=["builtins.classmethod"],
            return_type=return_type,
        )

    @contextmanager
    def if_(self, condition: str) -> Generator[CodeWriter, None, None]:
        """Create an if block"""
        self.writeln(f"if {condition}:")
        with self.indent():
            yield self

    @contextmanager
    def elif_(self, condition: str) -> Generator[CodeWriter, None, None]:
        """Create an elif block"""
        self.writeln(f"elif {condition}:")
        with self.indent():
            yield self

    @contextmanager
    def else_(self) -> Generator[CodeWriter, None, None]:
        """Create an else block"""
        self.writeln("else:")
        with self.indent():
            yield self

    @contextmanager
    def for_(
        self, var: str, iterable: str
    ) -> Generator[CodeWriter, None, None]:
        """Create a for loop"""
        self.writeln(f"for {var} in {iterable}:")
        with self.indent():
            yield self

    @contextmanager
    def while_(self, condition: str) -> Generator[CodeWriter, None, None]:
        """Create a while loop"""
        self.writeln(f"while {condition}:")
        with self.indent():
            yield self

    @contextmanager
    def try_(self) -> Generator[CodeWriter, None, None]:
        """Create a try block"""
        self.writeln("try:")
        with self.indent():
            yield self

    @contextmanager
    def except_(
        self, exception: Optional[str] = None, as_var: Optional[str] = None
    ) -> Generator[CodeWriter, None, None]:
        """Create an except block"""
        if exception and as_var:
            self.writeln(f"except {exception} as {as_var}:")
        elif exception:
            self.writeln(f"except {exception}:")
        else:
            self.writeln("except:")
        with self.indent():
            yield self

    @contextmanager
    def finally_(self) -> Generator[CodeWriter, None, None]:
        """Create a finally block"""
        self.writeln("finally:")
        with self.indent():
            yield self

    @contextmanager
    def with_(self, *contexts: str) -> Generator[CodeWriter, None, None]:
        """Create a with statement"""
        context_str = ", ".join(contexts)
        self.writeln(f"with {context_str}:")
        with self.indent():
            yield self

    def section(
        self, title: str, char: str = "=", width: int = 70
    ) -> CodeWriter:
        """Create a commented section divider"""
        self.blank_line()
        self.comment(char * width)
        self.comment(f" {title}")
        self.comment(char * width)
        self.blank_line()
        return self

    def module_docstring(self, text: str) -> CodeWriter:
        """Write a module-level docstring"""
        self.writeln(f'"""{text}"""')
        self.blank_line()
        return self

    def assignment(
        self, var: str, value: str, type_hint: Optional[str] = None
    ) -> CodeWriter:
        """Write a variable assignment"""
        if type_hint:
            self.writeln(f"{var}: {type_hint} = {value}")
        else:
            self.writeln(f"{var} = {value}")
        return self

    def return_(self, value: Optional[str] = None) -> CodeWriter:
        """Write a return statement"""
        if value:
            self.writeln(f"return {value}")
        else:
            self.writeln("return")
        return self

    def raise_(
        self, exception: str, message: Optional[str] = None
    ) -> CodeWriter:
        """Write a raise statement"""
        if message:
            self.writeln(f"raise {exception}({message!r})")
        else:
            self.writeln(f"raise {exception}")
        return self

    def yield_(self, value: str) -> CodeWriter:
        """Write a yield statement"""
        self.writeln(f"yield {value}")
        return self

    def assert_(
        self, condition: str, message: Optional[str] = None
    ) -> CodeWriter:
        """Write an assert statement"""
        if message:
            self.writeln(f"assert {condition}, {message!r}")
        else:
            self.writeln(f"assert {condition}")
        return self

    def pass_(self) -> CodeWriter:
        """Write a pass statement"""
        self.writeln("pass")
        return self

    def break_(self) -> CodeWriter:
        """Write a break statement"""
        self.writeln("break")
        return self

    def continue_(self) -> CodeWriter:
        """Write a continue statement"""
        self.writeln("continue")
        return self

    def generate_init(
        self, params_with_types: Mapping[str, str]
    ) -> CodeWriter:
        """Generate __init__ with automatic assignment"""
        params = ["self"] + [
            f"{name}: {type_}" for name, type_ in params_with_types.items()
        ]
        body = [f"self.{name} = {name}" for name in params_with_types.keys()]
        self.write_function("__init__", params, body)
        return self

    def generate_repr(
        self, class_name: str, fields: Iterable[str]
    ) -> CodeWriter:
        """Generate __repr__ method"""
        field_strs = ", ".join([f"{f}={{self.{f}!r}}" for f in fields])
        body = f"return f'{class_name}({field_strs})'"
        self.write_function(
            "__repr__", ["self"], body, return_type="builtins.str"
        )
        return self

    def generate_eq(self, fields: Iterable[str]) -> CodeWriter:
        """Generate __eq__ method"""
        comparisons = " and ".join([f"self.{f} == other.{f}" for f in fields])
        body = [
            "if not isinstance(other, self.__class__):",
            "    return False",
            f"return {comparisons}",
        ]
        self.write_function(
            "__eq__", ["self", "other"], body, return_type="builtins.bool"
        )
        return self

    def generate_str(
        self, class_name: str, fields: Iterable[str]
    ) -> CodeWriter:
        """Generate __str__ method"""
        field_strs = ", ".join([f"{f}={{self.{f}}}" for f in fields])
        body = f"return f'{class_name}({field_strs})'"
        self.write_function(
            "__str__", ["self"], body, return_type="builtins.str"
        )
        return self

    def generate_hash(self, fields: Iterable[str]) -> CodeWriter:
        """Generate __hash__ method"""
        if not fields:
            body = "return builtins.hash(builtins.id(self))"
        else:
            field_tuple = ", ".join([f"self.{f}" for f in fields])
            body = f"return builtins.hash(({field_tuple}))"
        self.write_function(
            "__hash__", ["self"], body, return_type="builtins.int"
        )
        return self

    def write_block(self, lines: Iterable[str]) -> CodeWriter:
        for line in lines:
            self.writeln(line)
        return self

    def blank_line(self, count: int = 1) -> CodeWriter:
        self._lines.extend([""] * count)
        return self

    def to_string(self) -> str:
        return "\n".join(self._lines)

    def to_lines(self) -> list[str]:
        return self._lines
