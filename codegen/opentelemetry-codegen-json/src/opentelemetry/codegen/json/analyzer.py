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
from dataclasses import dataclass
from typing import Optional

from google.protobuf import descriptor_pb2 as descriptor
from google.protobuf.compiler import plugin_pb2 as plugin

from opentelemetry.codegen.json.types import (
    to_json_field_name,
)

_logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ProtoType:
    """Represents a field type with its Python equivalent."""

    proto_type: int
    is_repeated: bool = False
    is_optional: bool = False
    is_message: bool = False
    is_enum: bool = False
    type_name: Optional[str] = None  # Fully qualified name for messages/enums


@dataclass(frozen=True, slots=True)
class FieldInfo:
    """Contains info about a message field."""

    name: str
    number: int
    field_type: ProtoType
    json_name: str
    default_value: Optional[str] = None
    oneof_index: Optional[int] = None
    is_oneof_member: bool = False


@dataclass(frozen=True, slots=True)
class EnumInfo:
    """Contains info about an enum."""

    name: str
    package: str
    file_name: str
    values: tuple[tuple[str, int], ...]  # List of (name, number) tuples
    parent_path: Optional[str] = (
        None  # Full parent class path (e.g. "Span.Event")
    )

    @property
    def python_class_path(self) -> str:
        """Get Python class path (e.g. 'Span.Event.EventType' for nested)."""
        if self.parent_path:
            return f"{self.parent_path}.{self.name}"
        return self.name

    @property
    def fully_qualified_name(self) -> str:
        """Get fully qualified proto name."""
        return f"{self.package}.{self.python_class_path}"


@dataclass(frozen=True, slots=True)
class MessageInfo:
    """Contains all info about a protobuf message."""

    name: str
    package: str
    file_name: str
    fields: tuple[FieldInfo, ...]
    nested_messages: tuple[MessageInfo, ...]
    nested_enums: tuple[EnumInfo, ...]
    parent_path: Optional[str] = (
        None  # Full parent class path (e.g. "Span.Event")
    )

    @property
    def fully_qualified_name(self) -> str:
        """Full proto package path."""
        return f"{self.package}.{self.python_class_path}"

    @property
    def python_class_path(self) -> str:
        """Path for nested classes in Python (e.g. 'Span.Event.SubEvent')."""
        if self.parent_path:
            return f"{self.parent_path}.{self.name}"
        return self.name


class DescriptorAnalyzer:
    """Analyzes protobuf descriptors and builds a structured representation."""

    def __init__(self, request: plugin.CodeGeneratorRequest) -> None:
        self._request = request
        self._messages: dict[
            str, MessageInfo
        ] = {}  # Maps fully_qualified_name -> MessageInfo
        self._enums: dict[
            str, EnumInfo
        ] = {}  # Maps fully_qualified_name -> EnumInfo
        self._file_to_messages: dict[str, list[MessageInfo]] = defaultdict(
            list
        )  # Maps proto file -> list of top level MessageInfo
        self._file_to_enums: dict[str, list[EnumInfo]] = defaultdict(
            list
        )  # Maps proto file -> list of top level EnumInfo
        self._file_dependencies: dict[str, list[str]] = defaultdict(
            list
        )  # Maps file -> list of imported files

    @property
    def messages(self) -> dict[str, MessageInfo]:
        """Get all messages indexed by fully qualified name."""
        return self._messages

    @property
    def enums(self) -> dict[str, EnumInfo]:
        """Get all enums indexed by fully qualified name."""
        return self._enums

    @property
    def file_to_messages(self) -> dict[str, list[MessageInfo]]:
        """Get top level messages for each file."""
        return self._file_to_messages

    @property
    def file_to_enums(self) -> dict[str, list[EnumInfo]]:
        """Get top level enums for each file."""
        return self._file_to_enums

    @property
    def file_dependencies(self) -> dict[str, list[str]]:
        """Get file dependencies."""
        return self._file_dependencies

    def analyze(self) -> None:
        """Process all files in the request."""
        for proto_file in self._request.proto_file:
            self._analyze_file(proto_file)

    def _analyze_file(
        self, file_descriptor: descriptor.FileDescriptorProto
    ) -> None:
        """Analyze a single proto file."""
        package = file_descriptor.package
        file_name = file_descriptor.name

        _logger.debug("Processing file: %s (package: %s)", file_name, package)

        self._file_dependencies[file_name] = list(file_descriptor.dependency)

        self._file_to_enums[file_name].extend(
            self._analyze_enum(enum_type, package, file_name, parent_path=None)
            for enum_type in file_descriptor.enum_type
        )
        self._file_to_messages[file_name].extend(
            self._analyze_message(
                message_type, package, file_name, parent_path=None
            )
            for message_type in file_descriptor.message_type
        )

    def _analyze_message(
        self,
        message_desc: descriptor.DescriptorProto,
        package: str,
        file_name: str,
        parent_path: Optional[str] = None,
    ) -> MessageInfo:
        """
        Recursively analyze message and nested types.

        Args:
            message_desc: The message descriptor
            package: The proto package name
            file_name: The proto file name
            parent_path: Full parent class path for nested messages (e.g. "Span.Event")

        Returns:
            MessageInfo for this message
        """
        # Determine the class path for nested types
        current_path = (
            f"{parent_path}.{message_desc.name}"
            if parent_path
            else message_desc.name
        )

        nested_enums = tuple(
            self._analyze_enum(enum_type, package, file_name, current_path)
            for enum_type in message_desc.enum_type
        )

        nested_messages = tuple(
            self._analyze_message(
                nested_type, package, file_name, current_path
            )
            for nested_type in message_desc.nested_type
            if not nested_type.options.map_entry  # Skip map entry types
        )

        fields = tuple(
            self._analyze_field(field_desc)
            for field_desc in message_desc.field
        )

        msg_info = MessageInfo(
            name=message_desc.name,
            package=package,
            file_name=file_name,
            fields=fields,
            nested_messages=nested_messages,
            nested_enums=nested_enums,
            parent_path=parent_path,
        )

        self._messages[msg_info.fully_qualified_name] = msg_info
        return msg_info

    def _analyze_field(
        self,
        field_desc: descriptor.FieldDescriptorProto,
    ) -> FieldInfo:
        """Analyze a single field."""
        is_repeated = (
            field_desc.label == descriptor.FieldDescriptorProto.LABEL_REPEATED
        )
        is_optional = field_desc.proto3_optional
        oneof_index = (
            field_desc.oneof_index
            if field_desc.HasField("oneof_index")
            else None
        )

        # Get JSON name
        json_name = (
            field_desc.json_name
            if field_desc.json_name
            else to_json_field_name(field_desc.name)
        )

        is_message = (
            field_desc.type == descriptor.FieldDescriptorProto.TYPE_MESSAGE
        )
        is_enum = field_desc.type == descriptor.FieldDescriptorProto.TYPE_ENUM
        type_name = (
            field_desc.type_name.lstrip(".")
            if field_desc.HasField("type_name")
            else None
        )

        proto_type = ProtoType(
            proto_type=field_desc.type,
            is_repeated=is_repeated,
            is_optional=is_optional,
            is_message=is_message,
            is_enum=is_enum,
            type_name=type_name,
        )

        return FieldInfo(
            name=field_desc.name,
            number=field_desc.number,
            field_type=proto_type,
            json_name=json_name,
            oneof_index=oneof_index,
            is_oneof_member=oneof_index is not None and not is_optional,
        )

    def _analyze_enum(
        self,
        enum_desc: descriptor.EnumDescriptorProto,
        package: str,
        file_name: str,
        parent_path: Optional[str] = None,
    ) -> EnumInfo:
        """
        Analyze an enum.

        Args:
            enum_desc: The enum descriptor
            package: The proto package name
            file_name: The proto file name
            parent_path: Full parent class path for nested enums (e.g. "Span.Event")

        Returns:
            EnumInfo for this enum
        """
        enum_info = EnumInfo(
            name=enum_desc.name,
            package=package,
            file_name=file_name,
            values=tuple(
                (value_desc.name, value_desc.number)
                for value_desc in enum_desc.value
            ),
            parent_path=parent_path,
        )

        self._enums[enum_info.fully_qualified_name] = enum_info
        return enum_info

    def get_message_by_name(
        self, fully_qualified_name: str
    ) -> Optional[MessageInfo]:
        """Get message by fully qualified name."""
        return self._messages.get(fully_qualified_name)

    def get_enum_by_name(
        self, fully_qualified_name: str
    ) -> Optional[EnumInfo]:
        """Get enum by fully qualified name."""
        return self._enums.get(fully_qualified_name)

    def get_messages_for_file(self, file_name: str) -> list[MessageInfo]:
        """Get top-level messages for a specific file."""
        return self._file_to_messages.get(file_name, [])
