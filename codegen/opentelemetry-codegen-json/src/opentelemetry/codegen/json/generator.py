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

import logging
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Callable, Final, Optional, Set

from google.protobuf import descriptor_pb2 as descriptor
from google.protobuf.compiler import plugin_pb2 as plugin

from opentelemetry.codegen.json.types import (
    get_default_value,
    get_json_allowed_types,
    get_python_type,
    is_bytes_type,
    is_hex_encoded_field,
    is_int64_type,
    to_json_field_name,
)
from opentelemetry.codegen.json.version import __version__ as GENERATOR_VERSION
from opentelemetry.codegen.json.writer import CodeWriter

_logger = logging.getLogger(__name__)

UTILS_MODULE_NAME: Final[str] = "_otlp_json_utils"


class OtlpJsonGenerator:
    """
    Generates Python dataclasses and JSON serialization/deserialization code
    from protobuf descriptors.
    """

    def __init__(
        self,
        request: plugin.CodeGeneratorRequest,
        package_transform: Callable[[str], str],
        version: str,
    ) -> None:
        """
        Initialize the generator.

        Args:
            request: Protobuf compiler plugin request
            package_transform: A callable that transforms the proto file path.
            version: Version string for the generated code.
        """
        self._request = request
        self._package_transform = package_transform
        self._version = version
        self._generated_files: dict[str, str] = {}
        self._common_root: str = ""
        self._file_to_proto: dict[str, descriptor.FileDescriptorProto] = {
            f.name: f for f in request.proto_file
        }
        self._fqn_to_file: dict[str, str] = {}
        self._fqn_to_class_path: dict[str, str] = {}
        self._file_dependencies: dict[str, list[str]] = {
            f.name: list(f.dependency) for f in request.proto_file
        }

        for proto_file in request.proto_file:
            self._index_file(proto_file)

    def generate_all(self) -> dict[str, str]:
        """
        Generate Python code for all proto files and support modules.

        Returns:
            Dictionary mapping output file paths to generated code
        """
        files_to_generate = self._request.file_to_generate
        file_to_output = {
            proto_file: self._transform_proto_path(proto_file)
            for proto_file in files_to_generate
        }

        if not file_to_output:
            return {}

        self._common_root = _find_common_root(file_to_output.values())

        for proto_file in files_to_generate:
            file_desc = self._file_to_proto[proto_file]
            code = self._generate_file(file_desc)
            output_path = file_to_output[proto_file]
            self._generated_files[output_path] = code

        utils_path = f"{self._common_root}/{UTILS_MODULE_NAME}.py"
        self._generated_files[utils_path] = _load_utils_source()

        version_init_path = f"{self._common_root}/version/__init__.py"
        version_writer = CodeWriter(indent_size=4)
        self._generate_header(version_writer)
        version_writer.writemany(f'__version__ = "{self._version}"', "")
        self._generated_files[version_init_path] = version_writer.to_string()

        self._ensure_init_files()

        return self._generated_files

    def _index_file(self, file_desc: descriptor.FileDescriptorProto) -> None:
        """
        Index all messages and enums in the file for usage during generation.

        Args:
            file_desc: File descriptor to index
        """
        package = file_desc.package
        for enum_desc in file_desc.enum_type:
            fqn = f"{package}.{enum_desc.name}" if package else enum_desc.name
            self._fqn_to_file[fqn] = file_desc.name
            self._fqn_to_class_path[fqn] = enum_desc.name
        for msg_desc in file_desc.message_type:
            self._index_message(msg_desc, package, file_desc.name, None)

    def _index_message(
        self,
        msg_desc: descriptor.DescriptorProto,
        package: str,
        file_name: str,
        parent_path: Optional[str],
    ) -> None:
        """
        Recursively index a message and its nested types.

        Args:
            msg_desc: Message descriptor to index
            package: Protobuf package name for the message
            file_name: Proto file where the message is defined
            parent_path: Full parent class path for nested messages
        """
        current_path = (
            f"{parent_path}.{msg_desc.name}" if parent_path else msg_desc.name
        )
        fqn = f"{package}.{current_path}" if package else current_path
        self._fqn_to_file[fqn] = file_name
        self._fqn_to_class_path[fqn] = current_path

        for enum_desc in msg_desc.enum_type:
            enum_fqn = f"{fqn}.{enum_desc.name}"
            self._fqn_to_file[enum_fqn] = file_name
            self._fqn_to_class_path[enum_fqn] = (
                f"{current_path}.{enum_desc.name}"
            )

        for nested_msg in msg_desc.nested_type:
            if not nested_msg.options.map_entry:
                self._index_message(
                    nested_msg, package, file_name, current_path
                )

    def _ensure_init_files(self) -> None:
        """
        Ensure that every directory in the output path contains an __init__.py file.
        """
        dirs = set()
        for path in self._generated_files:
            p = Path(path)
            for parent in p.parents:
                parent_str = str(parent)
                # Skip '.', root, and the 'opentelemetry' namespace directory
                if parent_str in (".", "/", "opentelemetry"):
                    continue
                dirs.add(parent_str)

        for d in dirs:
            init_path = f"{d}/__init__.py"
            if init_path not in self._generated_files:
                self._generated_files[init_path] = ""

    def _get_utils_module_path(self) -> str:
        """
        Get the absolute module path for the utility module.

        Returns:
            Absolute module path as a string
        """
        return (
            f"{self._common_root.replace('/', '.')}.{UTILS_MODULE_NAME}"
            if self._common_root
            else UTILS_MODULE_NAME
        )

    def _transform_proto_path(self, proto_path: str) -> str:
        """
        Transform proto file path to output Python file path.

        Example: 'opentelemetry/proto/trace/v1/trace.proto'
              -> 'opentelemetry/proto_json/trace/v1/trace.py'

        Args:
            proto_path: Original .proto file path

        Returns:
            Transformed .py file path
        """
        transformed = self._package_transform(proto_path)
        if transformed.endswith(".proto"):
            transformed = transformed[:-6] + ".py"
        return transformed

    def _get_module_path(self, proto_file: str) -> str:
        """
        Convert a proto file path to its transformed Python module path.

        Example: 'opentelemetry/proto/common/v1/common.proto'
              -> 'opentelemetry.proto_json.common.v1.common'

        Args:
            proto_file: Original .proto file path

        Returns:
            Python module path (dot-separated)
        """
        transformed = self._transform_proto_path(proto_file)
        if transformed.endswith(".py"):
            transformed = transformed[:-3]
        return transformed.replace("/", ".")

    def _generate_file(self, file_desc: descriptor.FileDescriptorProto) -> str:
        """
        Generate complete Python file for a proto file.

        Args:
            file_desc: File descriptor

        Returns:
            Generated Python code as string
        """
        writer = CodeWriter(indent_size=4)
        proto_file = file_desc.name

        self._generate_header(writer, proto_file)
        self._generate_imports(
            writer, proto_file, self._file_has_enums(file_desc)
        )
        self._generate_enums_for_file(writer, file_desc.enum_type)
        self._generate_messages_for_file(
            writer, proto_file, file_desc.message_type
        )
        writer.blank_line()

        return writer.to_string()

    def _file_has_enums(
        self, file_desc: descriptor.FileDescriptorProto
    ) -> bool:
        """
        Check if the file or any of its messages (recursively) contain enums.

        Args:
            file_desc: File descriptor to check
        Returns:
            True if any enums are found, False otherwise
        """
        if file_desc.enum_type:
            return True
        for msg in file_desc.message_type:
            if self._msg_has_enums(msg):
                return True
        return False

    def _msg_has_enums(self, msg_desc: descriptor.DescriptorProto) -> bool:
        """
        Recursively check if the message or any of its nested messages contain enums.

        Args:
            msg_desc: Message descriptor to check
        Returns:
            True if any enums are found, False otherwise
        """
        if msg_desc.enum_type:
            return True
        for nested in msg_desc.nested_type:
            if self._msg_has_enums(nested):
                return True
        return False

    def _generate_header(
        self, writer: CodeWriter, proto_file: str = ""
    ) -> None:
        """
        Generate file header with license and metadata.

        Args:
            writer: Code writer instance
            proto_file: Original proto file path (optional)
        """
        writer.comment(
            [
                "Copyright The OpenTelemetry Authors",
                "",
                'Licensed under the Apache License, Version 2.0 (the "License");',
                "you may not use this file except in compliance with the License.",
                "You may obtain a copy of the License at",
                "",
                "    http://www.apache.org/licenses/LICENSE-2.0",
                "",
                "Unless required by applicable law or agreed to in writing, software",
                'distributed under the License is distributed on an "AS IS" BASIS,',
                "WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.",
                "See the License for the specific language governing permissions and",
                "limitations under the License.",
            ]
        )
        writer.blank_line()
        if proto_file:
            writer.comment(f'AUTO-GENERATED from "{proto_file}"')
            writer.comment("DO NOT EDIT MANUALLY")
            writer.blank_line()

    def _generate_imports(
        self,
        writer: CodeWriter,
        proto_file: str,
        include_enum: bool,
    ) -> None:
        """
        Generate all necessary import statements.

        Args:
            writer: Code writer instance
            proto_file: Original proto file path
            include_enum: Whether to include the enum module import
        """
        writer.import_("__future__", "annotations")
        writer.blank_line()

        std_imports = [
            "builtins",
            "dataclasses",
            "functools",
            "json",
            "sys",
            "typing",
        ]
        if include_enum:
            std_imports.append("enum")

        for module in sorted(std_imports):
            writer.import_(module)

        writer.blank_line()

        with writer.if_("sys.version_info >= (3, 10)"):
            writer.assignment(
                "_dataclass",
                "functools.partial(dataclasses.dataclass, slots=True)",
            )
        with writer.else_():
            writer.assignment("_dataclass", "dataclasses.dataclass")
        writer.blank_line()

        # Collect all imports needed
        imports = self._collect_imports(proto_file)
        imports.add(f"import {self._get_utils_module_path()}")

        # Generate cross file imports
        if imports:
            for import_info in sorted(imports):
                writer.writeln(import_info)
            writer.blank_line()
        writer.blank_line()

    def _collect_imports(self, proto_file: str) -> Set[str]:
        """
        Collect all import statements needed for cross file references.

        Args:
            proto_file: Current proto file path

        Returns:
            Set of import statement strings
        """
        return set(
            "import " + self._get_module_path(dep_file)
            for dep_file in self._file_dependencies.get(proto_file, [])
        )

    def _generate_enums_for_file(
        self,
        writer: CodeWriter,
        enum_descs: Iterable[descriptor.EnumDescriptorProto],
    ) -> None:
        """
        Generate all enums for a file (top level and nested).

        Args:
            writer: Code writer instance
            enum_descs: List of top level enums
        """
        for enum_desc in enum_descs:
            self._generate_enum_class(writer, enum_desc)
            writer.blank_line()

    def _generate_messages_for_file(
        self,
        writer: CodeWriter,
        proto_file: str,
        msg_descs: Iterable[descriptor.DescriptorProto],
    ) -> None:
        """
        Generate all message classes for a file.

        Args:
            writer: Code writer instance
            proto_file: Original proto file path
            msg_descs: List of top level messages
        """
        for i, message in enumerate(msg_descs):
            if i:
                writer.blank_line(2)

            self._generate_message_class(writer, proto_file, message)

    def _generate_message_class(
        self,
        writer: CodeWriter,
        proto_file: str,
        msg_desc: descriptor.DescriptorProto,
        parent_path: Optional[str] = None,
    ) -> None:
        """
        Generate a complete dataclass for a protobuf message.

        Args:
            writer: Code writer instance
            proto_file: Original proto file path
            msg_desc: Message descriptor
            parent_path: Full parent class path for nested messages
        """
        current_path = (
            f"{parent_path}.{msg_desc.name}" if parent_path else msg_desc.name
        )
        with writer.dataclass(
            msg_desc.name,
            decorators=("typing.final",),
            decorator_name="_dataclass",
        ):
            if msg_desc.field or msg_desc.nested_type or msg_desc.enum_type:
                writer.docstring(
                    [f"Generated from protobuf message {msg_desc.name}"]
                )
                writer.blank_line()

            for enum_desc in msg_desc.enum_type:
                self._generate_enum_class(writer, enum_desc)
                writer.blank_line()

            for nested_desc in msg_desc.nested_type:
                if not nested_desc.options.map_entry:
                    self._generate_message_class(
                        writer, proto_file, nested_desc, current_path
                    )
                    writer.blank_line()

            if msg_desc.field:
                for field_desc in msg_desc.field:
                    self._generate_field(writer, proto_file, field_desc)
            else:
                writer.pass_()

            writer.blank_line()
            self._generate_to_dict(writer, msg_desc)
            writer.blank_line()
            self._generate_to_json(writer)
            writer.blank_line()
            self._generate_from_dict(
                writer, proto_file, msg_desc, current_path
            )
            writer.blank_line()
            self._generate_from_json(writer, current_path)

    def _generate_enum_class(
        self, writer: CodeWriter, enum_desc: descriptor.EnumDescriptorProto
    ) -> None:
        """
        Generate an IntEnum class for a protobuf enum.

        Args:
            writer: Code writer instance
            enum_desc: Enum descriptor
        """
        with writer.enum(
            enum_desc.name,
            enum_type="enum.IntEnum",
            decorators=("typing.final",),
        ):
            writer.docstring(
                [f"Generated from protobuf enum {enum_desc.name}"]
            )
            writer.blank_line()

            if enum_desc.value:
                for val_desc in enum_desc.value:
                    writer.enum_member(val_desc.name, val_desc.number)
            else:
                writer.pass_()

    def _generate_field(
        self,
        writer: CodeWriter,
        proto_file: str,
        field_desc: descriptor.FieldDescriptorProto,
    ) -> None:
        """
        Generate a dataclass field.

        Args:
            writer: Code writer instance
            proto_file: Original proto file path
            field_desc: Field descriptor
        """
        type_hint = self._get_field_type_hint(proto_file, field_desc)
        writer.field(
            field_desc.name,
            type_hint,
            default=self._get_field_default(field_desc),
        )

    def _generate_to_dict(
        self,
        writer: CodeWriter,
        msg_desc: descriptor.DescriptorProto,
    ) -> None:
        """
        Generate a to_dict() method that converts the dataclass instance to a dictionary

        Args:
            writer: Code writer instance
            msg_desc: Message descriptor for the class being generated
        """
        with writer.method(
            "to_dict",
            ["self"],
            return_type="builtins.dict[builtins.str, typing.Any]",
        ):
            writer.docstring(
                [
                    "Convert this message to a dictionary with lowerCamelCase keys.",
                    "",
                    "Returns:",
                    "    Dictionary representation following OTLP JSON encoding",
                ]
            )
            writer.assignment("_result", "{}")

            # Separate fields into oneof groups and standalone fields
            oneof_groups: dict[int, list[descriptor.FieldDescriptorProto]] = (
                defaultdict(list)
            )
            standalone_fields: list[descriptor.FieldDescriptorProto] = []

            for field in msg_desc.field:
                if field.HasField("oneof_index") and not field.proto3_optional:
                    oneof_groups[field.oneof_index].append(field)
                else:
                    standalone_fields.append(field)

            for field in standalone_fields:
                with writer.if_(f"self.{field.name}"):
                    self._generate_serialization_statements(
                        writer, field, "_result"
                    )

            for group_index in sorted(oneof_groups.keys()):
                group_fields = oneof_groups[group_index]
                for i, field in enumerate(reversed(group_fields)):
                    condition = f"self.{field.name} is not None"
                    context = (
                        writer.elif_(condition) if i else writer.if_(condition)
                    )

                    with context:
                        self._generate_serialization_statements(
                            writer, field, "_result"
                        )

            writer.return_("_result")

    def _generate_to_json(self, writer: CodeWriter) -> None:
        """
        Generate a to_json() method that serializes the message to a JSON string.

        Args:
            writer: Code writer instance
        """
        with writer.method("to_json", ["self"], return_type="builtins.str"):
            writer.docstring(
                [
                    "Serialize this message to a JSON string.",
                    "",
                    "Returns:",
                    "    JSON string",
                ]
            )
            writer.return_("json.dumps(self.to_dict())")

    def _generate_from_dict(
        self,
        writer: CodeWriter,
        proto_file: str,
        msg_desc: descriptor.DescriptorProto,
        current_path: str,
    ) -> None:
        """
        Generate a from_dict() class method that creates an instance from a dictionary.

        Args:
            writer: Code writer instance
            proto_file: Original proto file path
            msg_desc: Message descriptor for the class being generated
            current_path: Full class path for type hints and return type
        """
        with writer.method(
            "from_dict",
            ["cls", "data: builtins.dict[builtins.str, typing.Any]"],
            decorators=["builtins.classmethod"],
            return_type=f'"{current_path}"',
        ):
            writer.docstring(
                [
                    "Create from a dictionary with lowerCamelCase keys.",
                    "",
                    "Args:",
                    "    data: Dictionary representation following OTLP JSON encoding",
                    "",
                    "Returns:",
                    f"    {msg_desc.name} instance",
                ]
            )
            utils = self._get_utils_module_path()
            writer.writeln(
                f'{utils}.validate_type(data, builtins.dict, "data")'
            )
            writer.assignment("_args", "{}")
            writer.blank_line()

            # Separate fields into oneof groups and standalone fields
            oneof_groups: dict[int, list[descriptor.FieldDescriptorProto]] = (
                defaultdict(list)
            )
            standalone_fields: list[descriptor.FieldDescriptorProto] = []

            for field in msg_desc.field:
                if field.HasField("oneof_index") and not field.proto3_optional:
                    oneof_groups[field.oneof_index].append(field)
                else:
                    standalone_fields.append(field)

            # Handle standalone fields
            for field in standalone_fields:
                json_name = (
                    field.json_name
                    if field.json_name
                    else to_json_field_name(field.name)
                )
                with writer.if_(
                    f'(_value := data.get("{json_name}")) is not None'
                ):
                    self._generate_deserialization_statements(
                        writer, proto_file, field, "_value", "_args"
                    )

            # Handle oneof groups
            for group_index in sorted(oneof_groups.keys()):
                group_fields = oneof_groups[group_index]
                for i, field in enumerate(reversed(group_fields)):
                    json_name = (
                        field.json_name
                        if field.json_name
                        else to_json_field_name(field.name)
                    )
                    condition = (
                        f'(_value := data.get("{json_name}")) is not None'
                    )
                    context = (
                        writer.elif_(condition) if i else writer.if_(condition)
                    )

                    with context:
                        self._generate_deserialization_statements(
                            writer, proto_file, field, "_value", "_args"
                        )

            writer.blank_line()
            writer.return_("cls(**_args)")

    def _generate_from_json(
        self,
        writer: CodeWriter,
        current_path: str,
    ) -> None:
        """
        Generate a from_json() class method that creates an instance from a JSON string.

        Args:
            writer: Code writer instance
            current_path: Full class path for type hints and return type
        """
        with writer.method(
            "from_json",
            ["cls", "data: typing.Union[builtins.str, builtins.bytes]"],
            decorators=["builtins.classmethod"],
            return_type=f'"{current_path}"',
        ):
            writer.docstring(
                [
                    "Deserialize from a JSON string or bytes.",
                    "",
                    "Args:",
                    "    data: JSON string or bytes",
                    "",
                    "Returns:",
                    "    Instance of the class",
                ]
            )
            writer.return_("cls.from_dict(json.loads(data))")

    def _generate_serialization_statements(
        self,
        writer: CodeWriter,
        field_desc: descriptor.FieldDescriptorProto,
        target_dict: str,
    ) -> None:
        """
        Generate statements to serialize a field and assign it to the target dictionary.

        Args:
            writer: Code writer instance
            field_desc: Field descriptor for the field being serialized
            target_dict: Name of the dictionary variable to assign the serialized value to
        """
        json_name = (
            field_desc.json_name
            if field_desc.json_name
            else to_json_field_name(field_desc.name)
        )
        if field_desc.label == descriptor.FieldDescriptorProto.LABEL_REPEATED:
            item_expr = self._get_serialization_expr(field_desc, "_v")
            if item_expr == "_v":
                writer.assignment(
                    f'{target_dict}["{json_name}"]', f"self.{field_desc.name}"
                )
            else:
                utils = self._get_utils_module_path()
                writer.assignment(
                    f'{target_dict}["{json_name}"]',
                    f"{utils}.encode_repeated(self.{field_desc.name}, lambda _v: {item_expr})",
                )
        else:
            val_expr = self._get_serialization_expr(
                field_desc, f"self.{field_desc.name}"
            )
            writer.assignment(f'{target_dict}["{json_name}"]', val_expr)

    def _get_serialization_expr(
        self, field_desc: descriptor.FieldDescriptorProto, var_name: str
    ) -> str:
        """
        Get the Python expression to serialize a value of a given type for JSON output.

        Args:
            field_desc: Field descriptor for the value being serialized
            var_name: Variable name representing the value to serialize
        """
        utils = self._get_utils_module_path()
        if field_desc.type == descriptor.FieldDescriptorProto.TYPE_MESSAGE:
            return f"{var_name}.to_dict()"
        if field_desc.type == descriptor.FieldDescriptorProto.TYPE_ENUM:
            return f"builtins.int({var_name})"
        if is_hex_encoded_field(field_desc.name):
            return f"{utils}.encode_hex({var_name})"
        if is_int64_type(field_desc.type):
            return f"{utils}.encode_int64({var_name})"
        if is_bytes_type(field_desc.type):
            return f"{utils}.encode_base64({var_name})"
        if field_desc.type in (
            descriptor.FieldDescriptorProto.TYPE_FLOAT,
            descriptor.FieldDescriptorProto.TYPE_DOUBLE,
        ):
            return f"{utils}.encode_float({var_name})"

        return var_name

    def _generate_deserialization_statements(
        self,
        writer: CodeWriter,
        proto_file: str,
        field_desc: descriptor.FieldDescriptorProto,
        var_name: str,
        target_dict: str,
    ) -> None:
        """
        Generate statements to deserialize a field from a JSON value and assign it to the target dictionary.

        Args:
            writer: Code writer instance
            proto_file: Original proto file path
            field_desc: Field descriptor for the field being deserialized
            var_name: Variable name representing the JSON value to deserialize
            target_dict: Name of the dictionary variable to assign the deserialized value to
        """
        utils = self._get_utils_module_path()
        if field_desc.label == descriptor.FieldDescriptorProto.LABEL_REPEATED:
            item_expr = self._get_deserialization_expr(
                proto_file, field_desc, "_v"
            )
            writer.assignment(
                f'{target_dict}["{field_desc.name}"]',
                f'{utils}.decode_repeated({var_name}, lambda _v: {item_expr}, "{field_desc.name}")',
            )
            return

        if field_desc.type == descriptor.FieldDescriptorProto.TYPE_MESSAGE:
            msg_type = self._resolve_message_type(
                field_desc.type_name, proto_file
            )
            writer.assignment(
                f'{target_dict}["{field_desc.name}"]',
                f"{msg_type}.from_dict({var_name})",
            )
        elif field_desc.type == descriptor.FieldDescriptorProto.TYPE_ENUM:
            enum_type = self._resolve_enum_type(
                field_desc.type_name, proto_file
            )
            writer.writeln(
                f'{utils}.validate_type({var_name}, builtins.int, "{field_desc.name}")'
            )
            writer.assignment(
                f'{target_dict}["{field_desc.name}"]',
                f"{enum_type}({var_name})",
            )
        elif is_hex_encoded_field(field_desc.name):
            writer.assignment(
                f'{target_dict}["{field_desc.name}"]',
                f'{utils}.decode_hex({var_name}, "{field_desc.name}")',
            )
        elif is_int64_type(field_desc.type):
            writer.assignment(
                f'{target_dict}["{field_desc.name}"]',
                f'{utils}.decode_int64({var_name}, "{field_desc.name}")',
            )
        elif is_bytes_type(field_desc.type):
            writer.assignment(
                f'{target_dict}["{field_desc.name}"]',
                f'{utils}.decode_base64({var_name}, "{field_desc.name}")',
            )
        elif field_desc.type in (
            descriptor.FieldDescriptorProto.TYPE_FLOAT,
            descriptor.FieldDescriptorProto.TYPE_DOUBLE,
        ):
            writer.assignment(
                f'{target_dict}["{field_desc.name}"]',
                f'{utils}.decode_float({var_name}, "{field_desc.name}")',
            )
        else:
            allowed_types = get_json_allowed_types(
                field_desc.type, field_desc.name
            )
            writer.writeln(
                f'{utils}.validate_type({var_name}, {allowed_types}, "{field_desc.name}")'
            )
            writer.assignment(f'{target_dict}["{field_desc.name}"]', var_name)

    def _get_deserialization_expr(
        self,
        proto_file: str,
        field_desc: descriptor.FieldDescriptorProto,
        var_name: str,
    ) -> str:
        """
        Get the Python expression to deserialize a value of a given type for JSON input.

        Args:
            proto_file: Original proto file path
            field_desc: Field descriptor for the value being deserialized
            var_name: Variable name representing the JSON value to deserialize

        Returns:
            Python expression string to perform deserialization
        """
        utils = self._get_utils_module_path()
        if field_desc.type == descriptor.FieldDescriptorProto.TYPE_MESSAGE:
            msg_type = self._resolve_message_type(
                field_desc.type_name, proto_file
            )
            return f"{msg_type}.from_dict({var_name})"
        if field_desc.type == descriptor.FieldDescriptorProto.TYPE_ENUM:
            enum_type = self._resolve_enum_type(
                field_desc.type_name, proto_file
            )
            return f"{enum_type}({var_name})"
        if is_hex_encoded_field(field_desc.name):
            return f'{utils}.decode_hex({var_name}, "{field_desc.name}")'
        if is_int64_type(field_desc.type):
            return f'{utils}.decode_int64({var_name}, "{field_desc.name}")'
        if is_bytes_type(field_desc.type):
            return f'{utils}.decode_base64({var_name}, "{field_desc.name}")'
        if field_desc.type in (
            descriptor.FieldDescriptorProto.TYPE_FLOAT,
            descriptor.FieldDescriptorProto.TYPE_DOUBLE,
        ):
            return f'{utils}.decode_float({var_name}, "{field_desc.name}")'

        return var_name

    def _get_field_type_hint(
        self, proto_file: str, field_desc: descriptor.FieldDescriptorProto
    ) -> str:
        """
        Get the Python type hint for a field.

        Args:
            proto_file: Original proto file path
            field_desc: Field descriptor

        Returns:
            Python type hint string
        """
        if field_desc.type == descriptor.FieldDescriptorProto.TYPE_MESSAGE:
            base_type = self._resolve_message_type(
                field_desc.type_name, proto_file
            )
        elif field_desc.type == descriptor.FieldDescriptorProto.TYPE_ENUM:
            base_type = self._resolve_enum_type(
                field_desc.type_name, proto_file
            )
        else:
            base_type = get_python_type(field_desc.type)

        if field_desc.label == descriptor.FieldDescriptorProto.LABEL_REPEATED:
            return f"builtins.list[{base_type}]"
        if field_desc.type == descriptor.FieldDescriptorProto.TYPE_ENUM:
            return f"typing.Union[{base_type}, builtins.int, None]"
        return f"typing.Optional[{base_type}]"

    def _resolve_message_type(self, type_name: str, proto_file: str) -> str:
        """
        Resolve a message type name to its Python class path.

        Args:
            type_name: Fully qualified proto name
            proto_file: Current proto file path

        Returns:
            Python class reference
        """
        fqn = type_name.lstrip(".")
        target_file = self._fqn_to_file.get(fqn)

        if not target_file:
            _logger.warning("Could not resolve message type: %s", type_name)
            return "typing.Any"

        class_path = self._fqn_to_class_path[fqn]

        # If in same file, use relative class path
        if target_file == proto_file:
            return class_path
        # Cross file reference - use fully qualified module + class path
        module_path = self._get_module_path(target_file)
        return f"{module_path}.{class_path}"

    def _resolve_enum_type(self, type_name: str, proto_file: str) -> str:
        """
        Resolve an enum type name to its Python class path.

        Args:
            type_name: Fully qualified proto name
            proto_file: Current proto file path

        Returns:
            Python class reference
        """
        fqn = type_name.lstrip(".")
        target_file = self._fqn_to_file.get(fqn)

        if not target_file:
            _logger.warning("Could not resolve enum type: %s", type_name)
            return "builtins.int"

        class_path = self._fqn_to_class_path[fqn]

        # If in same file, use relative class path
        if target_file == proto_file:
            return class_path
        # Cross file reference - use fully qualified module + class path
        module_path = self._get_module_path(target_file)
        return f"{module_path}.{class_path}"

    def _get_field_default(
        self, field_desc: descriptor.FieldDescriptorProto
    ) -> Optional[str]:
        """
        Get the default value for a field.

        Args:
            field_desc: Field descriptor

        Returns:
            Default value string or None
        """
        # Repeated fields default to empty list
        if field_desc.label == descriptor.FieldDescriptorProto.LABEL_REPEATED:
            return "dataclasses.field(default_factory=builtins.list)"

        # Optional fields, Message types, and oneof members default to None
        if field_desc.type == descriptor.FieldDescriptorProto.TYPE_MESSAGE or (
            field_desc.HasField("oneof_index")
            and not field_desc.proto3_optional
        ):
            return "None"

        # Enum types default to 0
        if field_desc.type == descriptor.FieldDescriptorProto.TYPE_ENUM:
            return "0"

        # Primitive types use proto defaults
        return get_default_value(field_desc.type)


def _load_utils_source() -> str:
    """
    Load the source code for the utility module from its source file.

    Returns:
        Source code as a string
    """
    utils_src_path = Path(__file__).parent / "runtime" / "otlp_json_utils.py"
    try:
        return utils_src_path.read_text(encoding="utf-8")
    except Exception as e:
        _logger.error(
            "Failed to load utility module source from %s: %s",
            utils_src_path,
            e,
        )
        raise RuntimeError(
            f"Failed to load utility module source from {utils_src_path}"
        ) from e


def _find_common_root(paths: Iterable[str]) -> str:
    """
    Find the longest common directory prefix among the given paths.

    Args:
        paths: Iterable of file paths to analyze
    Returns:
        Common directory prefix as a string
    """
    if not paths:
        return ""

    # Split paths into components
    split_paths = [p.split("/")[:-1] for p in paths]
    if not split_paths:
        return ""

    # Find common prefix among components
    common = []
    for parts in zip(*split_paths):
        if all(p == parts[0] for p in parts):
            common.append(parts[0])
        else:
            break

    return "/".join(common)


def generate_code(
    request: plugin.CodeGeneratorRequest,
    package_transform: Callable[[str], str] = lambda p: p.replace(
        "opentelemetry/proto/", "opentelemetry/proto_json/"
    ),
) -> dict[str, str]:
    """
    Main entry point for code generation.

    Args:
        request: Protobuf compiler plugin request
        package_transform: Package transformation string or callable

    Returns:
        Dictionary mapping output file paths to generated code
    """
    generator = OtlpJsonGenerator(
        request, package_transform, version=GENERATOR_VERSION
    )
    return generator.generate_all()


def generate_plugin_response(
    request: plugin.CodeGeneratorRequest,
    package_transform: Callable[[str], str] = lambda p: p.replace(
        "opentelemetry/proto/", "opentelemetry/proto_json/"
    ),
) -> plugin.CodeGeneratorResponse:
    """
    Generate plugin response with all generated files.

    Args:
        request: Protobuf compiler plugin request
        package_transform: Package transformation string

    Returns:
        Plugin response with generated files
    """
    response = plugin.CodeGeneratorResponse()

    # Declare support for optional proto3 fields
    response.supported_features |= (
        plugin.CodeGeneratorResponse.FEATURE_PROTO3_OPTIONAL
    )
    response.supported_features |= (
        plugin.CodeGeneratorResponse.FEATURE_SUPPORTS_EDITIONS
    )

    response.minimum_edition = descriptor.EDITION_LEGACY
    response.maximum_edition = descriptor.EDITION_2024

    # Generate code
    generated_files = generate_code(request, package_transform)

    # Create response files
    for output_path, code in generated_files.items():
        file_response = response.file.add()
        file_response.name = output_path
        file_response.content = code

    return response
