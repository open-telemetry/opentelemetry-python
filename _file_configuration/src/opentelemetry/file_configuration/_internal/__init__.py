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

from collections import OrderedDict
from os import environ
from pathlib import Path
from re import compile as re_compile
from abc import ABC, abstractmethod
from logging import getLogger
from datetime import datetime
from random import random

from typing import Optional, Sequence
from opentelemetry.trace import Link, SpanKind
from opentelemetry.trace.span import TraceState
from opentelemetry.util.types import Attributes
from opentelemetry.context import Context

from ipdb import set_trace
from jinja2 import Environment, FileSystemLoader
from jsonref import JsonRef
from jsonref import loads as jsonref_loads
from jsonschema.validators import Draft202012Validator
from yaml import safe_load
from black import format_str, Mode
from opentelemetry.util._importlib_metadata import entry_points

from opentelemetry.file_configuration._internal.path_function import path_function
from opentelemetry.sdk.trace.sampling import Sampler, SamplingResult

_logger = getLogger(__file__)

set_trace

_environment_variable_regex = re_compile(r"\$\{([a-zA-Z]\w*)\}")
_type_type = {
    "integer": int,
    "boolean": bool,
    "string": str,
    "array": list,
    "object": object,
    "number": float,
}

_path_function = path_function


def get_path_function() -> dict:
    return _path_function


def set_path_function(path_function: dict) -> None:
    global _path_function
    _path_function = path_function


class FileConfigurationPlugin(ABC):

    @property
    @abstractmethod
    def schema(self) -> dict:
        """
        Returns the plugin schema.
        """

    @property
    @abstractmethod
    def schema_path(self) -> list:
        """
        Returns the path for the plugin schema.
        """

    @staticmethod
    @abstractmethod
    def function(*args, **kwargs) -> object:
        """
        The function that will instantiate the plugin object.
        """

    @property
    def recursive_path(self) -> list:
        """
        The recursive path for the plugin object if any.
        """
        return []


class SometimesMondaysOnSampler(Sampler):
    """
    A sampler that samples only on Mondays, but sometimes.
    """

    def __init__(self, probability: float) -> None:
        super().__init__(probability)
        self._probability = probability

    def should_sample(
        self,
        parent_context: Optional["Context"],
        trace_id: int,
        name: str,
        kind: SpanKind = None,
        attributes: Attributes = None,
        links: Sequence["Link"] = None,
        trace_state: "TraceState" = None,
    ) -> SamplingResult:
        return datetime.now().weekday() == 0 and random() < self._probability

    def get_description(self) -> str:
        return self.__class__.__name__


class SometimesMondaysOnSamplerPlugin(FileConfigurationPlugin):

    @property
    def schema(self) -> tuple:
        """
        Returns the plugin schema.
        """
        return (
            "sometimes_mondays_on",
            {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "probability": {
                        "type": "number"
                    },
                }
            }
        )

    @property
    def schema_path(self) -> list:
        """
        Returns the path for the plugin schema.
        """
        return [
            "properties",
            "tracer_provider",
            "properties",
            "sampler",
            "properties"
        ]

    @staticmethod
    def function(probability: float) -> SometimesMondaysOnSampler:
        """
        The function that will instantiate the plugin object.
        """
        return SometimesMondaysOnSampler(probability)


def resolve_schema(json_file_path) -> dict:

    root_path = json_file_path.absolute()

    with open(json_file_path, "r") as json_file:
        resolved_schema = jsonref_loads(
            json_file.read(), base_uri=root_path.as_uri()
        )

    for entry_point in entry_points(group="opentelemetry_file_configuration"):

        plugin = entry_point.load()()

        sub_resolved_schema = resolved_schema

        schema_path = []

        for schema_path_part in plugin.schema_path:
            schema_path.append(schema_path_part)
            try:
                sub_resolved_schema = sub_resolved_schema[schema_path_part]
            except KeyError:
                _logger.warning(
                    "Unable to add plugin %s to schema: wrong schema path %s",
                    entry_point.name,
                    ",".join(schema_path)
                )
                break
        else:
            sub_resolved_schema[plugin.schema[0]] = plugin.schema[1]

        original_path_function = get_path_function()
        sub_path_function = original_path_function

        for schema_path_part in plugin.schema_path:

            if schema_path_part == "properties":
                continue

            sub_path_function = (
                sub_path_function[schema_path_part]["children"]
            )

        sub_path_function[plugin.schema[0]] = {}
        sub_path_function[plugin.schema[0]]["function"] = plugin.function
        sub_path_function[plugin.schema[0]]["children"] = {}
        sub_path_function[plugin.schema[0]]["recursive_path"] = (
            plugin.recursive_path
        )

    set_path_function(original_path_function)

    return resolved_schema


def load_file_configuration(file_configuration_file_path: str) -> dict:

    with open(file_configuration_file_path, "r") as file_configuration_file:

        return safe_load(file_configuration_file)


def validate_file_configuration(
    schema: dict,
    file_configuration: dict
) -> None:
    Draft202012Validator(schema).validate(file_configuration)


def process_schema(schema: dict) -> dict:
    def traverse(
        schema: dict,
        schema_value_id_stack: list,
        schema_key_stack: list,
        recursive_path: list,
        processed_schema: dict,
    ):
        schema_value_type = schema.get("type")

        if schema_value_type == "array":
            traverse(
                schema["items"],
                schema_value_id_stack,
                schema_key_stack,
                recursive_path,
                processed_schema,
            )

        elif schema_value_type == "object":

            schema_properties = schema.get("properties", {})

            all_attributes = set(schema_properties.keys())

            positional_attributes = set(schema.get("required", []))

            optional_attributes = all_attributes.difference(
                positional_attributes
            )

            positional_attributes = sorted(list(positional_attributes))
            optional_attributes = sorted(list(optional_attributes))

            result_positional_attributes = OrderedDict()
            result_optional_attributes = OrderedDict()

            for positional_attribute in positional_attributes:

                result_positional_attributes[positional_attribute] = (
                    _type_type[
                        schema_properties[positional_attribute]["type"]
                    ].__name__
                )

            for optional_attribute in optional_attributes:

                result_optional_attributes[optional_attribute] = (
                    _type_type[
                        schema_properties[optional_attribute]["type"]
                    ].__name__
                )

            children = {}

            children.update(result_positional_attributes)
            children.update(result_optional_attributes)

            processed_schema[schema_key_stack[-1]] = {
                "function_name": "_".join(schema_key_stack[1:]),
                "positional_attributes": result_positional_attributes,
                "optional_attributes": result_optional_attributes,
                "additional_properties": (
                    schema.get("additionalProperties", False)
                    or "patternProperties" in schema.keys()
                ),
                "recursive_path": recursive_path,
                "children": children,
            }

            if recursive_path:
                return

            for (
                schema_properties_key,
                schema_properties_value,
            ) in schema_properties.items():

                schema_properties_value_type = schema_properties_value.get(
                    "type"
                )

                if (
                    schema_properties_value_type != "object"
                    and schema_properties_value_type != "array"
                ):
                    continue

                if isinstance(schema_properties_value, JsonRef):
                    schema_properties_value_id = id(
                        schema_properties_value.__subject__
                    )

                else:
                    schema_properties_value_id = id(schema_properties_value)

                is_recursive = (
                    schema_properties_value_id in schema_value_id_stack
                )

                schema_value_id_stack.append(schema_properties_value_id)
                schema_key_stack.append(schema_properties_key)

                recursive_path = []

                if is_recursive:

                    for (
                        current_schema_key_stack,
                        current_schema_value_id,
                    ) in zip(schema_key_stack[1:], schema_value_id_stack):
                        recursive_path.append(current_schema_key_stack)
                        if (
                            schema_properties_value_id
                            == current_schema_value_id
                        ):
                            break

                traverse(
                    schema_properties_value,
                    schema_value_id_stack,
                    schema_key_stack,
                    recursive_path,
                    children,
                )

                schema_value_id_stack.pop()
                schema_key_stack.pop()

    processed_schema = {}

    traverse(schema, [], [""], [], processed_schema)

    return processed_schema[""]["children"]


def render_schema(processed_schema: dict, path_function_path: Path):
    def traverse(
        processed_schema: dict,
        schema_function: dict,
        function_arguments: dict,
    ):

        for (
            processed_schema_key,
            processed_schema_value,
        ) in processed_schema.items():

            if not isinstance(processed_schema_value, dict):
                continue

            function_arguments[processed_schema_value["function_name"]] = {
                "optional_attributes": (
                    processed_schema_value["optional_attributes"]
                ),
                "positional_attributes": (
                    processed_schema_value["positional_attributes"]
                ),
                "additional_properties": (
                    processed_schema_value["additional_properties"]
                ),
            }

            schema_function_children = {}
            schema_function[processed_schema_key] = {
                "function": processed_schema_value["function_name"],
                "children": schema_function_children,
                "recursive_path": processed_schema_value["recursive_path"],
            }

            children = processed_schema_value["children"]

            if children:
                traverse(
                    children, schema_function_children, function_arguments
                )

    schema_function = {}
    function_arguments = {}
    traverse(processed_schema, schema_function, function_arguments)

    current_path = Path(__file__).parent

    environment = Environment(
        loader=FileSystemLoader(current_path.joinpath("templates"))
    )

    with open(path_function_path, "w") as result_py_file:

        result_py_file.write(
            "\n".join(
                [
                    f"{line}  # noqa" if len(line) > 80 else line
                    for line in environment.get_template("template.jinja2")
                    .render(locals())
                    .split("\n")
                ]
            )
        )


def create_object(
    file_configuration: dict,
    processed_schema: dict,
    object_name: str,
    dry_run=False
) -> object:
    def create_object(
        file_configuration: dict,
        processed_schema: dict,
        path_function: dict,
        original_processed_schema: dict,
        original_path_function: dict,
    ) -> object:

        positional_arguments = []
        optional_arguments = {}

        for file_configuration_key, file_configuration_value in file_configuration.items():

            if isinstance(file_configuration_value, dict):

                if processed_schema["recursive_path"]:

                    new_processed_schema = original_processed_schema
                    new_path_function = original_path_function

                    for path in processed_schema["recursive_path"]:
                        new_processed_schema = new_processed_schema[path][
                            "children"
                        ]
                        new_path_function = new_path_function[path]["children"]

                    new_processed_schema = new_processed_schema[
                        file_configuration_key
                    ]
                    new_path_function = new_path_function[file_configuration_key]
                else:
                    new_processed_schema = processed_schema["children"][
                        file_configuration_key
                    ]
                    new_path_function = path_function["children"][
                        file_configuration_key
                    ]

                object_ = create_object(
                    file_configuration_value,
                    new_processed_schema,
                    new_path_function,
                    original_processed_schema,
                    original_path_function,
                )

            elif isinstance(file_configuration_value, list):

                object_ = []

                for element in file_configuration_value:

                    object_.append(
                        create_object(
                            element,
                            processed_schema["children"][file_configuration_key],
                            path_function["children"][file_configuration_key],
                            original_processed_schema,
                            original_path_function,
                        )
                    )

            else:

                object_ = file_configuration_value

            if file_configuration_key in (
                processed_schema["positional_attributes"].keys()
            ):
                positional_arguments.append(object_)

            else:
                optional_arguments[file_configuration_key] = object_

        return path_function["function"](
            *positional_arguments, **optional_arguments
        )

    path_function = get_path_function()

    result = create_object(
        file_configuration[object_name],
        processed_schema[object_name],
        path_function[object_name],
        processed_schema,
        path_function,
    )
    if dry_run:
        return format_str(repr(result), mode=Mode(line_length=1))
    return result


def substitute_environment_variables(
    file_configuration: dict, processed_schema: dict
) -> dict:
    def traverse(
        file_configuration: dict,
        processed_schema: dict,
        original_processed_schema: dict,
    ):

        for file_configuration_key, file_configuration_value in file_configuration.items():

            if file_configuration_key not in processed_schema.keys():
                continue

            if isinstance(file_configuration_value, dict):

                recursive_paths = processed_schema[file_configuration_key][
                    "recursive_path"
                ]

                if recursive_paths:

                    children = original_processed_schema

                    for recursive_path in recursive_paths:
                        children = children[recursive_path]["children"]

                else:
                    children = processed_schema[file_configuration_key]["children"]

                traverse(
                    file_configuration_value, children, original_processed_schema
                )

            elif isinstance(file_configuration_value, list):

                for element in file_configuration_value:
                    if isinstance(element, dict):
                        traverse(
                            element,
                            processed_schema[file_configuration_key]["children"],
                            original_processed_schema,
                        )

            elif isinstance(file_configuration_value, str):

                match = _environment_variable_regex.match(file_configuration_value)

                if match is not None:

                    file_configuration[file_configuration_key] = __builtins__[
                        processed_schema[file_configuration_key]
                    ](environ.get(match.group(1)))

    traverse(file_configuration, processed_schema, processed_schema)

    return file_configuration
