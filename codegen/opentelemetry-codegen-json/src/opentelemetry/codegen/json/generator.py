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
from pathlib import Path
from typing import Callable, Final, Optional, Set, Union

from google.protobuf import descriptor_pb2 as descriptor
from google.protobuf.compiler import plugin_pb2 as plugin

from opentelemetry.codegen.json.descriptor_analyzer import (
    DescriptorAnalyzer,
    EnumInfo,
    FieldInfo,
    MessageInfo,
    ProtoType,
)
from opentelemetry.codegen.json.types import (
    get_default_value,
    get_python_type,
    is_bytes_type,
    is_hex_encoded_field,
    is_int64_type,
)
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
        analyzer: DescriptorAnalyzer,
        package_transform: Callable[[str], str],
    ) -> None:
        """
        Initialize the generator.

        Args:
            analyzer: Analyzed descriptor information
            package_transform: A callable that transforms the proto file path.
        """
        self._analyzer = analyzer
        self._package_transform = package_transform
        self._generated_files: dict[str, str] = {}
        self._common_root: str = ""

    def generate_all(self) -> dict[str, str]:
        """
        Generate Python code for all proto files and support modules.

        Returns:
            Dictionary mapping output file paths to generated code
        """
        all_proto_files = set(self._analyzer.file_to_messages.keys()) | set(
            self._analyzer.file_to_enums.keys()
        )

        file_to_output = {
            proto_file: self._transform_proto_path(proto_file)
            for proto_file in all_proto_files
            if self._analyzer.file_to_messages.get(proto_file)
            or self._analyzer.file_to_enums.get(proto_file)
        }

        if not file_to_output:
            return {}

        self._common_root = self._find_common_root(
            list(file_to_output.values())
        )

        for proto_file, output_path in file_to_output.items():
            messages = self._analyzer.file_to_messages.get(proto_file, [])
            enums = self._analyzer.file_to_enums.get(proto_file, [])
            code = self._generate_file(proto_file, messages, enums)
            self._generated_files[output_path] = code

        utils_path = f"{self._common_root}/{UTILS_MODULE_NAME}.py"
        self._generated_files[utils_path] = self._load_utils_source()

        self._ensure_init_files()

        return self._generated_files

    def _load_utils_source(self) -> str:
        """Load the source code for the utility module from its source file."""
        utils_src_path = (
            Path(__file__).parent / "runtime" / "otlp_json_utils.py"
        )
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

    def _find_common_root(self, paths: list[str]) -> str:
        """Find the longest common directory prefix."""
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

    def _ensure_init_files(self) -> None:
        """Ensure every directory in the output contains an __init__.py file."""
        dirs = set()
        for path in list(self._generated_files.keys()):
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
                self._generated_files[init_path] = (
                    "# AUTO-GENERATED - DO NOT EDIT\n"
                )

    def _get_utils_module_path(self) -> str:
        """Get the absolute module path for the utility module."""
        if not self._common_root:
            return UTILS_MODULE_NAME
        return f"{self._common_root.replace('/', '.')}.{UTILS_MODULE_NAME}"

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

    def _generate_file(
        self,
        proto_file: str,
        messages: list[MessageInfo],
        enums: list[EnumInfo],
    ) -> str:
        """
        Generate complete Python file for a proto file.

        Args:
            proto_file: Original proto file path
            messages: List of top-level messages in this file
            enums: List of top-level enums in this file

        Returns:
            Generated Python code as string
        """
        writer = CodeWriter(indent_size=4)

        self._generate_header(writer, proto_file)
        self._generate_imports(writer, proto_file)
        self._generate_enums_for_file(writer, enums)
        self._generate_messages_for_file(writer, messages)

        return writer.to_string()

    def _generate_header(self, writer: CodeWriter, proto_file: str) -> None:
        """Generate file header with license and metadata."""
        writer.writemany(
            "# Copyright The OpenTelemetry Authors",
            "#",
            '# Licensed under the Apache License, Version 2.0 (the "License");',
            "# you may not use this file except in compliance with the License.",
            "# You may obtain a copy of the License at",
            "#",
            "#     http://www.apache.org/licenses/LICENSE-2.0",
            "#",
            "# Unless required by applicable law or agreed to in writing, software",
            '# distributed under the License is distributed on an "AS IS" BASIS,',
            "# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.",
            "# See the License for the specific language governing permissions and",
            "# limitations under the License.",
        )
        writer.blank_line()
        writer.comment(f'AUTO-GENERATED from "{proto_file}"')
        writer.comment("DO NOT EDIT MANUALLY")
        writer.blank_line()
        writer.writeln("from __future__ import annotations")
        writer.blank_line()

    def _generate_imports(
        self,
        writer: CodeWriter,
        proto_file: str,
    ) -> None:
        """
        Generate all necessary import statements.

        Args:
            writer: Code writer instance
            proto_file: Original proto file path
        """
        # Standard library imports
        writer.import_("json")
        writer.import_("typing", "Any", "Optional", "Union", "Self")
        writer.import_("dataclasses", "dataclass", "field")
        writer.import_("enum", "IntEnum")
        writer.blank_line()

        # Collect all imports needed for cross-file references
        imports = self._collect_imports(proto_file)

        # Import the generated utility module
        utils_module = self._get_utils_module_path()
        imports.add(f"import {utils_module} as _utils")

        # Generate cross file imports
        if imports:
            for import_info in sorted(imports):
                writer.writeln(import_info)
            writer.blank_line()

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
            for dep_file in self._analyzer.file_dependencies.get(
                proto_file, []
            )
        )

    def _generate_enums_for_file(
        self,
        writer: CodeWriter,
        enums: list[EnumInfo],
    ) -> None:
        """
        Generate all enums for a file (top-level and nested).

        Args:
            writer: Code writer instance
            enums: List of top-level enums
        """
        for enum_info in enums:
            self._generate_enum_class(writer, enum_info)
            writer.blank_line()

    def _generate_messages_for_file(
        self, writer: CodeWriter, messages: list[MessageInfo]
    ) -> None:
        """
        Generate all message classes for a file.

        Args:
            writer: Code writer instance
            messages: List of top-level messages
        """
        for i, message in enumerate(messages):
            if i:
                writer.blank_line(2)

            self._generate_message_class(writer, message)

    def _generate_message_class(
        self, writer: CodeWriter, message: MessageInfo
    ) -> None:
        """
        Generate a complete dataclass for a protobuf message.

        Args:
            writer: Code writer instance
            message: Message information
        """
        with writer.dataclass(
            message.name,
            frozen=False,  # Allow mutation for builder pattern if needed
            slots=True,  # Use slots for better performance
        ):
            if (
                message.fields
                or message.nested_messages
                or message.nested_enums
            ):
                writer.docstring(
                    [f"Generated from protobuf message {message.name}"]
                )
                writer.blank_line()

            for enum_info in message.nested_enums:
                self._generate_enum_class(writer, enum_info)
                writer.blank_line()

            for nested_msg in message.nested_messages:
                self._generate_message_class(writer, nested_msg)
                writer.blank_line()

            if message.fields:
                for field_info in message.fields:
                    self._generate_field(writer, field_info, message)
            else:
                # Empty dataclass needs a pass statement
                writer.pass_()

            writer.blank_line()
            self._generate_to_dict(writer, message)
            writer.blank_line()
            self._generate_to_json(writer, message)
            writer.blank_line()
            self._generate_from_dict(writer, message)
            writer.blank_line()
            self._generate_from_json(writer, message)

    def _generate_to_dict(
        self, writer: CodeWriter, message: MessageInfo
    ) -> None:
        """Generate to_dict() method."""
        with writer.method("to_dict", ["self"], return_type="dict[str, Any]"):
            writer.docstring(
                [
                    "Convert this message to a dictionary with lowerCamelCase keys.",
                    "",
                    "Returns:",
                    "    Dictionary representation following OTLP JSON encoding",
                ]
            )
            writer.writeln("_result: dict[str, Any] = {}")

            for field in message.fields:
                field_type = field.field_type
                if field_type.is_repeated:
                    item_expr = self._get_serialization_expr_for_type(
                        field_type, field.name, "_v"
                    )
                    with writer.if_(f"self.{field.name}"):
                        if item_expr == "_v":
                            writer.writeln(
                                f'_result["{field.json_name}"] = self.{field.name}'
                            )
                        else:
                            writer.writeln(
                                f'_result["{field.json_name}"] = _utils.serialize_repeated('
                                f"self.{field.name}, lambda _v: {item_expr})"
                            )
                else:
                    val_expr = self._get_serialization_expr_for_type(
                        field_type, field.name, f"self.{field.name}"
                    )
                    default = get_default_value(field_type.proto_type)
                    check = (
                        f"self.{field.name} is not None"
                        if field_type.is_message
                        else f"self.{field.name} != {default}"
                    )

                    with writer.if_(check):
                        writer.writeln(
                            f'_result["{field.json_name}"] = {val_expr}'
                        )

            writer.return_("_result")

    def _generate_to_json(
        self, writer: CodeWriter, message: MessageInfo
    ) -> None:
        """Generate to_json() method."""
        with writer.method("to_json", ["self"], return_type="str"):
            writer.docstring(
                [
                    "Serialize this message to a JSON string.",
                    "",
                    "Returns:",
                    "    JSON string",
                ]
            )
            writer.return_("json.dumps(self.to_dict())")

    def _get_serialization_expr_for_type(
        self, field_type: ProtoType, field_name: str, var_name: str
    ) -> str:
        """Get the Python expression to serialize a value of a given type."""
        if field_type.is_message:
            return f"{var_name}.to_dict()"
        if field_type.is_enum:
            return f"int({var_name})"
        if is_hex_encoded_field(field_name):
            return f"_utils.encode_hex({var_name})"
        if is_int64_type(field_type.proto_type):
            return f"_utils.encode_int64({var_name})"
        if is_bytes_type(field_type.proto_type):
            return f"_utils.encode_base64({var_name})"
        if field_type.proto_type in (
            descriptor.FieldDescriptorProto.TYPE_FLOAT,
            descriptor.FieldDescriptorProto.TYPE_DOUBLE,
        ):
            return f"_utils.encode_float({var_name})"

        return var_name

    def _generate_from_dict(
        self, writer: CodeWriter, message: MessageInfo
    ) -> None:
        """Generate from_dict() class method."""
        with writer.method(
            "from_dict",
            ["cls", "data: dict[str, Any]"],
            decorators=["classmethod"],
            return_type="Self",
        ):
            writer.docstring(
                [
                    "Create from a dictionary with lowerCamelCase keys.",
                    "",
                    "Args:",
                    "    data: Dictionary representation following OTLP JSON encoding",
                    "",
                    "Returns:",
                    f"    {message.name} instance",
                ]
            )
            writer.writeln("_args: dict[str, Any] = {}")

            for field in message.fields:
                field_type = field.field_type
                with writer.if_(
                    f'(_value := data.get("{field.json_name}")) is not None'
                ):
                    if field_type.is_repeated:
                        item_expr = self._get_deserialization_expr_for_type(
                            field_type, field.name, "_v", message
                        )
                        if item_expr == "_v":
                            writer.writeln(f'_args["{field.name}"] = _value')
                        else:
                            writer.writeln(
                                f'_args["{field.name}"] = _utils.deserialize_repeated('
                                f"_value, lambda _v: {item_expr})"
                            )
                    else:
                        val_expr = self._get_deserialization_expr_for_type(
                            field_type, field.name, "_value", message
                        )
                        writer.writeln(f'_args["{field.name}"] = {val_expr}')

            writer.return_("cls(**_args)")

    def _generate_from_json(
        self, writer: CodeWriter, message: MessageInfo
    ) -> None:
        """Generate from_json() class method."""
        with writer.method(
            "from_json",
            ["cls", "data: Union[str, bytes]"],
            decorators=["classmethod"],
            return_type="Self",
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

    def _get_deserialization_expr_for_type(
        self,
        field_type: ProtoType,
        field_name: str,
        var_name: str,
        context: MessageInfo,
    ) -> str:
        """Get the Python expression to deserialize a value of a given type."""
        if field_type.is_message and (type_name := field_type.type_name):
            msg_type = self._resolve_message_type(type_name, context)
            return f"{msg_type}.from_dict({var_name})"
        if field_type.is_enum and (type_name := field_type.type_name):
            enum_type = self._resolve_enum_type(type_name, context)
            return f"{enum_type}({var_name})"
        if is_hex_encoded_field(field_name):
            return f"_utils.decode_hex({var_name})"
        if is_int64_type(field_type.proto_type):
            return f"_utils.parse_int64({var_name})"
        if is_bytes_type(field_type.proto_type):
            return f"_utils.decode_base64({var_name})"
        if field_type.proto_type in (
            descriptor.FieldDescriptorProto.TYPE_FLOAT,
            descriptor.FieldDescriptorProto.TYPE_DOUBLE,
        ):
            return f"_utils.parse_float({var_name})"

        return var_name

    def _generate_enum_class(
        self, writer: CodeWriter, enum_info: EnumInfo
    ) -> None:
        """
        Generate an IntEnum class for a protobuf enum.

        Args:
            writer: Code writer instance
            enum_info: Enum information
        """
        with writer.enum(enum_info.name, enum_type="IntEnum"):
            writer.docstring(
                [f"Generated from protobuf enum {enum_info.name}"]
            )
            writer.blank_line()

            if enum_info.values:
                for name, number in enum_info.values:
                    writer.enum_member(name, number)
            else:
                writer.pass_()

    def _generate_field(
        self,
        writer: CodeWriter,
        field_info: FieldInfo,
        parent_message: MessageInfo,
    ) -> None:
        """
        Generate a dataclass field.

        Args:
            writer: Code writer instance
            field_info: Field information
            parent_message: Parent message (for context)
        """
        type_hint = self._get_field_type_hint(field_info, parent_message)
        default = self._get_field_default(field_info)

        if default:
            writer.field(field_info.name, type_hint, default=default)
        else:
            writer.field(field_info.name, type_hint)

    def _get_field_type_hint(
        self, field_info: FieldInfo, parent_message: MessageInfo
    ) -> str:
        """
        Get the Python type hint for a field.

        Args:
            field_info: Field information
            parent_message: Parent message (for resolving nested types)

        Returns:
            Python type hint string
        """
        field_type = field_info.field_type

        if field_type.is_message and (type_name := field_type.type_name):
            base_type = self._resolve_message_type(type_name, parent_message)
        elif field_type.is_enum and (type_name := field_type.type_name):
            base_type = self._resolve_enum_type(type_name, parent_message)
        else:
            base_type = get_python_type(field_type.proto_type)

        if field_type.is_repeated:
            return f"list[{base_type}]"
        elif field_type.is_optional:
            return f"Optional[{base_type}]"
        else:
            return base_type

    def _resolve_message_type(
        self, fully_qualified_name: str, context_message: MessageInfo
    ) -> str:
        """
        Resolve a message type name to its Python class path.

        Args:
            fully_qualified_name: Fully qualified proto name (e.g. 'package.Message')
            context_message: Current message (for resolving nested types)

        Returns:
            Python class reference (e.g. 'Message' or 'ParentMessage.NestedMessage')
        """
        # Look up the message in the analyzer
        message_info = self._analyzer.get_message_by_name(fully_qualified_name)

        if message_info is None:
            _logger.warning(
                "Could not resolve message type: %s", fully_qualified_name
            )
            return "Any"

        # If in same file, use relative class path
        if message_info.file_name == context_message.file_name:
            return message_info.python_class_path
        else:
            # Cross file reference - use fully qualified module + class path
            module_path = self._get_module_path(message_info.file_name)
            return f"{module_path}.{message_info.python_class_path}"

    def _resolve_enum_type(
        self, fully_qualified_name: str, context_message: MessageInfo
    ) -> str:
        """
        Resolve an enum type name to its Python class path.

        Args:
            fully_qualified_name: Fully qualified proto name
            context_message: Current message (for resolving nested types)

        Returns:
            Python class reference
        """
        enum_info = self._analyzer.get_enum_by_name(fully_qualified_name)

        if enum_info is None:
            _logger.warning(
                "Could not resolve enum type: %s", fully_qualified_name
            )
            return "int"

        # If in same file, use relative class path
        if enum_info.file_name == context_message.file_name:
            return enum_info.python_class_path
        else:
            # Cross file reference - use fully qualified module + class path
            module_path = self._get_module_path(enum_info.file_name)
            return f"{module_path}.{enum_info.python_class_path}"

    def _get_field_default(self, field_info: FieldInfo) -> Optional[str]:
        """
        Get the default value for a field.

        Args:
            field_info: Field information

        Returns:
            Default value string or None
        """
        field_type = field_info.field_type

        # Repeated fields default to empty list
        if field_type.is_repeated:
            return "field(default_factory=list)"

        # Optional fields and Message types default to None
        if field_type.is_optional or field_type.is_message:
            return "None"

        # Enum types default to 0
        if field_type.is_enum:
            return "0"

        # Primitive types - use proto defaults
        return get_default_value(field_type.proto_type)


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
    analyzer = DescriptorAnalyzer(request)
    analyzer.analyze()

    generator = OtlpJsonGenerator(analyzer, package_transform)
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
