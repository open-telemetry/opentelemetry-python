# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=no-member,invalid-name,too-many-lines

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from google.protobuf import descriptor_pb2 as descriptor
from google.protobuf.compiler import plugin_pb2 as plugin

from opentelemetry.codegen.pyproto.types import (
    INT_BOUNDS,
    PACKED_WIRE_HELPER,
    SINGULAR_WIRE_HELPER,
    get_default_value,
    get_python_type,
)
from opentelemetry.codegen.pyproto.writer import CodeWriter

_logger = logging.getLogger(__name__)

_FD = descriptor.FieldDescriptorProto

_RUNTIME_PKG = "opentelemetry._proto._pyprotobuf"

# Inline value encoders for oneof members and proto3-optional scalars. These are
# written even when the value equals the proto3 default, so the field helpers
# (which omit defaults) cannot be used. Each entry maps a proto scalar type to:
#   (wire_type_constant, value_expression_template, {kernel_functions}, need_pack)
# The template's ``{v}`` placeholder is replaced with the attribute expression.
# TYPE_STRING and TYPE_BYTES are handled specially (length prefix) by the caller.
_INLINE_SCALAR: dict[int, tuple[str, str, set[str], bool]] = {
    _FD.TYPE_BOOL: ("WT_VARINT", "encode_varint(1 if {v} else 0)", {"encode_varint"}, False),
    _FD.TYPE_INT32: ("WT_VARINT", "encode_int({v})", {"encode_int"}, False),
    _FD.TYPE_INT64: ("WT_VARINT", "encode_int({v})", {"encode_int"}, False),
    _FD.TYPE_UINT32: ("WT_VARINT", "encode_varint({v})", {"encode_varint"}, False),
    _FD.TYPE_UINT64: ("WT_VARINT", "encode_varint({v})", {"encode_varint"}, False),
    _FD.TYPE_SINT32: ("WT_VARINT", "encode_sint32({v})", {"encode_sint32"}, False),
    _FD.TYPE_SINT64: ("WT_VARINT", "encode_sint64({v})", {"encode_sint64"}, False),
    _FD.TYPE_DOUBLE: ("WT_64BIT", 'pack("<d", {v})', set(), True),
    _FD.TYPE_FLOAT: ("WT_32BIT", 'pack("<f", {v})', set(), True),
    _FD.TYPE_FIXED64: ("WT_64BIT", "encode_fixed64({v})", {"encode_fixed64"}, False),
    _FD.TYPE_SFIXED64: ("WT_64BIT", "encode_sfixed64({v})", {"encode_sfixed64"}, False),
    _FD.TYPE_FIXED32: ("WT_32BIT", "encode_fixed32({v})", {"encode_fixed32"}, False),
    _FD.TYPE_SFIXED32: ("WT_32BIT", "encode_sfixed32({v})", {"encode_sfixed32"}, False),
}


class PyProtoGenerator:
    """Generate pure-Python, encode-only protobuf-wire message classes."""

    def __init__(
        self,
        request: plugin.CodeGeneratorRequest,
        package_transform: Callable[[str], str],
    ) -> None:
        self._request = request
        self._package_transform = package_transform
        self._generated_files: dict[str, str] = {}
        self._file_to_proto: dict[str, descriptor.FileDescriptorProto] = {f.name: f for f in request.proto_file}
        self._fqn_to_file: dict[str, str] = {}
        self._fqn_to_class_path: dict[str, str] = {}
        self._fqn_is_enum: dict[str, bool] = {}
        self._file_dependencies: dict[str, list[str]] = {f.name: list(f.dependency) for f in request.proto_file}

        # Per-file import tracking, reset in _generate_file.
        self._used_helpers: set[str] = set()
        self._used_kernel: set[str] = set()
        self._used_wt: set[str] = set()
        self._need_pack: bool = False
        self._need_intenum: bool = False
        self._cross_imports: set[tuple[str, str]] = set()

        for proto_file in request.proto_file:
            self._index_file(proto_file)

    # ---- indexing --------------------------------------------------------

    def _index_file(self, file_desc: descriptor.FileDescriptorProto) -> None:
        package = file_desc.package
        for enum_desc in file_desc.enum_type:
            fqn = f"{package}.{enum_desc.name}" if package else enum_desc.name
            self._fqn_to_file[fqn] = file_desc.name
            self._fqn_to_class_path[fqn] = enum_desc.name
            self._fqn_is_enum[fqn] = True
        for msg_desc in file_desc.message_type:
            self._index_message(msg_desc, package, file_desc.name, None)

    def _index_message(
        self,
        msg_desc: descriptor.DescriptorProto,
        package: str,
        file_name: str,
        parent_path: str | None,
    ) -> None:
        current_path = f"{parent_path}.{msg_desc.name}" if parent_path else msg_desc.name
        fqn = f"{package}.{current_path}" if package else current_path
        self._fqn_to_file[fqn] = file_name
        self._fqn_to_class_path[fqn] = current_path
        self._fqn_is_enum[fqn] = False

        for enum_desc in msg_desc.enum_type:
            enum_fqn = f"{fqn}.{enum_desc.name}"
            self._fqn_to_file[enum_fqn] = file_name
            self._fqn_to_class_path[enum_fqn] = f"{current_path}.{enum_desc.name}"
            self._fqn_is_enum[enum_fqn] = True

        for nested_msg in msg_desc.nested_type:
            if not nested_msg.options.map_entry:
                self._index_message(nested_msg, package, file_name, current_path)

    # ---- orchestration ---------------------------------------------------

    def generate_all(self) -> dict[str, str]:
        files_to_generate = self._request.file_to_generate
        file_to_output = {p: self._transform_proto_path(p) for p in files_to_generate}
        if not file_to_output:
            return {}

        for proto_file in files_to_generate:
            file_desc = self._file_to_proto[proto_file]
            self._generated_files[file_to_output[proto_file]] = self._generate_file(file_desc)

        self._ensure_init_files()
        return self._generated_files

    def _transform_proto_path(self, proto_path: str) -> str:
        transformed = self._package_transform(proto_path)
        if transformed.endswith(".proto"):
            transformed = transformed[:-6] + "_pb2.py"
        return transformed

    def _get_module_path(self, proto_file: str) -> str:
        transformed = self._transform_proto_path(proto_file)
        transformed = transformed.removesuffix(".py")
        return transformed.replace("/", ".")

    def _ensure_init_files(self) -> None:
        dirs: set[str] = set()
        for path in self._generated_files:
            for parent in Path(path).parents:
                parent_str = str(parent)
                if parent_str in (".", "/"):
                    continue
                dirs.add(parent_str)
        for d in dirs:
            init_path = f"{d}/__init__.py"
            if init_path not in self._generated_files:
                self._generated_files[init_path] = ""

    # ---- file generation -------------------------------------------------

    def _generate_file(self, file_desc: descriptor.FileDescriptorProto) -> str:
        self._used_helpers = set()
        self._used_kernel = set()
        self._used_wt = set()
        self._need_pack = False
        self._need_intenum = False
        self._cross_imports = set()

        proto_file = file_desc.name
        body = CodeWriter(indent_size=4)

        for enum_desc in file_desc.enum_type:
            self._generate_enum_class(body, enum_desc)
            body.blank_line(2)

        for i, message in enumerate(file_desc.message_type):
            if i:
                body.blank_line(2)
            self._generate_message_class(body, proto_file, message)

        # protobuf lifts top-level enum values to module scope and exposes
        # ``global___<Name>`` aliases for every top-level enum and message.
        # Reproduce both so the public surface matches the generated code.
        self._generate_module_aliases(body, file_desc)

        header = CodeWriter(indent_size=4)
        self._generate_header(header, proto_file)
        imports = self._render_imports()

        return header.to_string() + "\n" + imports + "\n\n" + body.to_string() + "\n"

    @classmethod
    def _generate_header(cls, writer: CodeWriter, proto_file: str = "") -> None:
        writer.comment(
            [
                "Copyright The OpenTelemetry Authors",
                "SPDX-License-Identifier: Apache-2.0",
            ]
        )
        writer.blank_line()
        if proto_file:
            writer.comment(f'AUTO-GENERATED from "{proto_file}"')
            writer.comment("DO NOT EDIT MANUALLY")

    def _render_imports(self) -> str:
        writer = CodeWriter(indent_size=4)
        writer.import_("__future__", "annotations")
        writer.blank_line()
        if self._need_intenum:
            writer.import_("enum", "IntEnum")
        if self._need_pack:
            writer.import_("struct", "pack")
        if self._need_intenum or self._need_pack:
            writer.blank_line()
        if self._used_kernel:
            writer.import_(_RUNTIME_PKG, *sorted(self._used_kernel))
        if self._used_helpers or self._used_wt:
            writer.import_(f"{_RUNTIME_PKG}.fields", *sorted(self._used_helpers | self._used_wt))
        writer.import_(f"{_RUNTIME_PKG}.message", "Message")
        for module, name in sorted(self._cross_imports):
            writer.import_(module, name)
        return writer.to_string()

    # ---- enums -----------------------------------------------------------

    def _generate_enum_class(self, writer: CodeWriter, enum_desc: descriptor.EnumDescriptorProto) -> None:
        self._need_intenum = True
        with writer.enum(enum_desc.name, enum_type="IntEnum"):
            if enum_desc.value:
                for val_desc in enum_desc.value:
                    writer.enum_member(val_desc.name, val_desc.number)
            else:
                writer.pass_()

    def _generate_module_aliases(self, writer: CodeWriter, file_desc: descriptor.FileDescriptorProto) -> None:
        for enum_desc in file_desc.enum_type:
            # Lift the top-level enum's values to module scope.
            for val_desc in enum_desc.value:
                writer.writeln(f"{val_desc.name} = {enum_desc.name}.{val_desc.name}")
            writer.blank_line()
            writer.writeln(f"global___{enum_desc.name} = {enum_desc.name}")
            writer.blank_line()
        for msg_desc in file_desc.message_type:
            writer.writeln(f"global___{msg_desc.name} = {msg_desc.name}")

    # ---- messages --------------------------------------------------------

    def _generate_message_class(
        self,
        writer: CodeWriter,
        proto_file: str,
        msg_desc: descriptor.DescriptorProto,
        parent_path: str | None = None,
    ) -> None:
        current_path = f"{parent_path}.{msg_desc.name}" if parent_path else msg_desc.name
        with writer.class_(msg_desc.name, bases=("Message",)):
            for enum_desc in msg_desc.enum_type:
                self._generate_enum_class(writer, enum_desc)
                writer.blank_line()
                # Lift enum members onto the parent message as class attributes.
                for val_desc in enum_desc.value:
                    writer.writeln(f"{val_desc.name} = {enum_desc.name}.{val_desc.name}")
                writer.blank_line()

            for nested_desc in msg_desc.nested_type:
                if not nested_desc.options.map_entry:
                    self._generate_message_class(writer, proto_file, nested_desc, current_path)
                    writer.blank_line()

            oneof_members = self._real_oneof_members(msg_desc)
            self._generate_init(writer, proto_file, msg_desc, oneof_members)
            writer.blank_line()
            if oneof_members:
                self._generate_oneof_accessors(writer, proto_file, msg_desc, oneof_members)
                self._generate_which_oneof(writer, msg_desc, oneof_members)
                writer.blank_line()
            self._generate_serialize(writer, proto_file, msg_desc, oneof_members)

    @staticmethod
    def _real_oneof_members(
        msg_desc: descriptor.DescriptorProto,
    ) -> dict[int, list[descriptor.FieldDescriptorProto]]:
        groups: dict[int, list[descriptor.FieldDescriptorProto]] = defaultdict(list)
        for field in msg_desc.field:
            if field.HasField("oneof_index") and not field.proto3_optional:
                groups[field.oneof_index].append(field)
        return dict(groups)

    def _generate_init(
        self,
        writer: CodeWriter,
        proto_file: str,
        msg_desc: descriptor.DescriptorProto,
        oneof_members: dict[int, list[descriptor.FieldDescriptorProto]],
    ) -> None:
        oneof_field_names = {f.name for members in oneof_members.values() for f in members}

        params = ["self"]
        for field in msg_desc.field:
            params.append(f"{field.name}: {self._param_hint(proto_file, field)} = {self._param_default(field)}")

        with writer.method("__init__", params, return_type="None"):
            if not msg_desc.field:
                writer.pass_()
                return

            # Regular (non-oneof) fields.
            for field in msg_desc.field:
                if field.name in oneof_field_names:
                    continue
                self._generate_init_assignment(writer, proto_file, field)

            # Oneof groups: initialise the backing fields, then assign any
            # provided member through its property setter, which coerces a dict,
            # applies the range check, and selects the member.
            for oneof_index in sorted(oneof_members):
                oneof_name = msg_desc.oneof_decl[oneof_index].name
                members = oneof_members[oneof_index]
                for field in members:
                    writer.assignment(f"self._{field.name}", "None")
                writer.assignment(f"self._which_{oneof_name}", "None")
                for field in members:
                    with writer.if_(f"{field.name} is not None"):
                        writer.assignment(f"self.{field.name}", field.name)

    def _generate_init_assignment(
        self,
        writer: CodeWriter,
        proto_file: str,
        field: descriptor.FieldDescriptorProto,
    ) -> None:
        if field.label == _FD.LABEL_REPEATED:
            writer.assignment(f"self.{field.name}", f"list({field.name}) if {field.name} else []")
            return
        if field.type == _FD.TYPE_MESSAGE:
            msg_type = self._resolve_type(field.type_name, proto_file)
            with writer.if_(f"isinstance({field.name}, dict)"):
                writer.assignment(field.name, f"{msg_type}(**{field.name})")
            writer.assignment(f"self.{field.name}", field.name)
            return
        writer.assignment(f"self.{field.name}", field.name)

    def _generate_oneof_accessors(
        self,
        writer: CodeWriter,
        proto_file: str,
        msg_desc: descriptor.DescriptorProto,
        oneof_members: dict[int, list[descriptor.FieldDescriptorProto]],
    ) -> None:
        for oneof_index in sorted(oneof_members):
            oneof_name = msg_desc.oneof_decl[oneof_index].name
            members = oneof_members[oneof_index]
            names_tuple = ", ".join(f'"{f.name}"' for f in members)
            with writer.method(f"_select_{oneof_name}", ["self", "name", "value"], return_type="None"):
                with writer.for_("_f", f"({names_tuple},)"):
                    writer.writeln('setattr(self, f"_{_f}", value if _f == name else None)')
                writer.assignment(f"self._which_{oneof_name}", "name")
            writer.blank_line()
            for field in members:
                self._generate_oneof_property(writer, proto_file, oneof_name, field)
                writer.blank_line()

    def _generate_oneof_property(
        self,
        writer: CodeWriter,
        proto_file: str,
        oneof_name: str,
        field: descriptor.FieldDescriptorProto,
    ) -> None:
        name = field.name
        writer.writeln("@property")
        with writer.method(name, ["self"]):
            if field.type == _FD.TYPE_MESSAGE:
                msg_type = self._resolve_type(field.type_name, proto_file)
                with writer.if_(f"self._{name} is None"):
                    writer.writeln(f'self._select_{oneof_name}("{name}", {msg_type}())')
            writer.return_(f"self._{name}")
        writer.blank_line()
        writer.writeln(f"@{name}.setter")
        with writer.method(name, ["self", "value"], return_type="None"):
            if field.type in INT_BOUNDS:
                lo, hi = INT_BOUNDS[field.type]
                with writer.if_(f"value is not None and not {lo} <= value < {hi}"):
                    writer.writeln(f'raise ValueError("Value out of range for {name}: " + repr(value))')
            with writer.if_("value is None"):
                writer.assignment(f"self._{name}", "None")
                with writer.if_(f'self._which_{oneof_name} == "{name}"'):
                    writer.assignment(f"self._which_{oneof_name}", "None")
            with writer.else_():
                if field.type == _FD.TYPE_MESSAGE:
                    msg_type = self._resolve_type(field.type_name, proto_file)
                    with writer.if_("isinstance(value, dict)"):
                        writer.assignment("value", f"{msg_type}(**value)")
                writer.writeln(f'self._select_{oneof_name}("{name}", value)')

    def _generate_which_oneof(
        self,
        writer: CodeWriter,
        msg_desc: descriptor.DescriptorProto,
        oneof_members: dict[int, list[descriptor.FieldDescriptorProto]],
    ) -> None:
        with writer.method("WhichOneof", ["self", "oneof_name: str"], return_type="str | None"):
            for oneof_index in sorted(oneof_members):
                oneof_name = msg_desc.oneof_decl[oneof_index].name
                with writer.if_(f'oneof_name == "{oneof_name}"'):
                    writer.return_(f"self._which_{oneof_name}")
            writer.return_("None")

    def _generate_serialize(
        self,
        writer: CodeWriter,
        proto_file: str,
        msg_desc: descriptor.DescriptorProto,
        oneof_members: dict[int, list[descriptor.FieldDescriptorProto]],
    ) -> None:
        oneof_of_field: dict[str, str] = {}
        for oneof_index, members in oneof_members.items():
            oneof_name = msg_desc.oneof_decl[oneof_index].name
            for field in members:
                oneof_of_field[field.name] = oneof_name

        with writer.method("SerializeToString", ["self"], return_type="bytes"):
            writer.assignment("result", 'b""')
            for field in sorted(msg_desc.field, key=lambda f: f.number):
                if field.name in oneof_of_field:
                    self._emit_oneof_field(writer, proto_file, field, oneof_of_field[field.name])
                else:
                    self._emit_regular_field(writer, proto_file, field)
            writer.return_("result")

    def _emit_regular_field(
        self,
        writer: CodeWriter,
        proto_file: str,
        field: descriptor.FieldDescriptorProto,
    ) -> None:
        n = field.number
        if field.label == _FD.LABEL_REPEATED:
            if field.type == _FD.TYPE_MESSAGE:
                self._use_helper("msg")
                writer.writeln(f'result += b"".join(msg({n}, _v.SerializeToString()) for _v in self.{field.name})')
            elif field.type in PACKED_WIRE_HELPER:
                helper = PACKED_WIRE_HELPER[field.type]
                self._use_helper(helper)
                writer.writeln(f"result += {helper}({n}, self.{field.name})")
            else:
                # Non-packed repeated scalar (string, bytes).
                helper = SINGULAR_WIRE_HELPER[field.type]
                self._use_helper(helper)
                writer.writeln(f'result += b"".join({helper}({n}, _v) for _v in self.{field.name})')
            return

        if field.type == _FD.TYPE_MESSAGE:
            self._use_helper("msg")
            with writer.if_(f"self.{field.name} is not None"):
                writer.writeln(f"result += msg({n}, self.{field.name}.SerializeToString())")
            return

        if field.proto3_optional:
            self._emit_optional_scalar(writer, field)
            return

        # Singular scalar / enum.
        if field.type == _FD.TYPE_ENUM:
            self._use_helper("u64")
            writer.writeln(f"result += u64({n}, self.{field.name})")
            return
        helper = SINGULAR_WIRE_HELPER[field.type]
        self._use_helper(helper)
        writer.writeln(f"result += {helper}({n}, self.{field.name})")

    def _emit_optional_scalar(self, writer: CodeWriter, field: descriptor.FieldDescriptorProto) -> None:
        n = field.number
        if field.type == _FD.TYPE_DOUBLE:
            self._use_helper("opt_dbl")
            writer.writeln(f"result += opt_dbl({n}, self.{field.name})")
            return
        # Other proto3-optional scalars: written (even at default) only when set.
        with writer.if_(f"self.{field.name} is not None"):
            self._emit_inline_scalar(writer, field, f"self.{field.name}")

    def _emit_oneof_field(
        self,
        writer: CodeWriter,
        proto_file: str,
        field: descriptor.FieldDescriptorProto,
        oneof_name: str,
    ) -> None:
        n = field.number
        with writer.if_(f"self._{field.name} is not None"):
            if field.type == _FD.TYPE_MESSAGE:
                self._use_helper("msg")
                writer.writeln(f"result += msg({n}, self._{field.name}.SerializeToString())")
            else:
                self._emit_inline_scalar(writer, field, f"self._{field.name}")

    def _emit_inline_scalar(
        self,
        writer: CodeWriter,
        field: descriptor.FieldDescriptorProto,
        value_expr: str,
    ) -> None:
        """Emit ``result += <tag> + <value>`` for a value always written to wire."""
        n = field.number
        self._used_kernel.add("encode_tag")
        if field.type == _FD.TYPE_STRING:
            self._used_kernel.add("encode_varint")
            self._used_wt.add("WT_LEN")
            writer.assignment("_utf8", f"{value_expr}.encode('utf-8')")
            writer.writeln(f"result += encode_tag({n}, WT_LEN) + encode_varint(len(_utf8)) + _utf8")
            return
        if field.type == _FD.TYPE_BYTES:
            self._used_kernel.add("encode_varint")
            self._used_wt.add("WT_LEN")
            writer.assignment("_bv", value_expr)
            writer.writeln(f"result += encode_tag({n}, WT_LEN) + encode_varint(len(_bv)) + _bv")
            return
        wt, template, kernels, need_pack = _INLINE_SCALAR[field.type]
        self._used_wt.add(wt)
        self._used_kernel |= kernels
        if need_pack:
            self._need_pack = True
        value = template.format(v=value_expr)
        writer.writeln(f"result += encode_tag({n}, {wt}) + {value}")

    def _use_helper(self, name: str) -> None:
        self._used_helpers.add(name)

    # ---- type resolution -------------------------------------------------

    def _resolve_type(self, type_name: str, proto_file: str) -> str:
        fqn = type_name.lstrip(".")
        target_file = self._fqn_to_file.get(fqn)
        if not target_file:
            _logger.warning("Could not resolve type: %s", type_name)
            return "typing.Any"
        class_path = self._fqn_to_class_path[fqn]
        if target_file == proto_file:
            return class_path
        module = self._get_module_path(target_file)
        top = class_path.split(".")[0]
        self._cross_imports.add((module, top))
        return class_path

    def _param_hint(self, proto_file: str, field: descriptor.FieldDescriptorProto) -> str:
        if field.type == _FD.TYPE_MESSAGE or field.type == _FD.TYPE_ENUM:
            base = self._resolve_type(field.type_name, proto_file)
        else:
            base = get_python_type(field.type)
        if field.label == _FD.LABEL_REPEATED:
            return f"list[{base}] | None"
        return f"{base} | None"

    def _param_default(self, field: descriptor.FieldDescriptorProto) -> str:
        if field.label == _FD.LABEL_REPEATED:
            return "None"
        if field.type == _FD.TYPE_MESSAGE or field.HasField("oneof_index") or field.proto3_optional:
            return "None"
        if field.type == _FD.TYPE_ENUM:
            return "0"
        return get_default_value(field.type)


def generate_code(
    request: plugin.CodeGeneratorRequest,
    package_transform: Callable[[str], str] = lambda p: p.replace("opentelemetry/proto/", "opentelemetry/_proto/"),
) -> dict[str, str]:
    return PyProtoGenerator(request, package_transform).generate_all()


def generate_plugin_response(
    request: plugin.CodeGeneratorRequest,
    package_transform: Callable[[str], str] = lambda p: p.replace("opentelemetry/proto/", "opentelemetry/_proto/"),
) -> plugin.CodeGeneratorResponse:
    response = plugin.CodeGeneratorResponse()
    response.supported_features |= plugin.CodeGeneratorResponse.FEATURE_PROTO3_OPTIONAL
    response.supported_features |= plugin.CodeGeneratorResponse.FEATURE_SUPPORTS_EDITIONS
    response.minimum_edition = descriptor.EDITION_LEGACY
    response.maximum_edition = descriptor.EDITION_2024
    for output_path, code in generate_code(request, package_transform).items():
        file_response = response.file.add()
        file_response.name = output_path
        file_response.content = code
    return response
