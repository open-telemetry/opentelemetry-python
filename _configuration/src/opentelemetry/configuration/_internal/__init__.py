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

from ipdb import set_trace
from os import environ
from yaml import safe_load
from re import compile as re_compile
from jsonref import JsonRef
from os.path import exists
from pathlib import Path
from collections import OrderedDict
from json import loads as json_loads
from jsonref import loads as jsonref_loads
from jsonschema.validators import Draft202012Validator
from referencing import Registry, Resource
from opentelemetry.configuration._internal.path_function import path_function
from jinja2 import Environment, FileSystemLoader

set_trace

_environment_variable_regex = re_compile(r"\$\{([a-zA-Z]\w*)\}")
_type_type = {
    "integer": int,
    "boolean": bool,
    "string": str,
    "array": list,
    "object": object,
    "number": float
}


def resolve_schema(json_file_path) -> dict:

    root_path = json_file_path.absolute()

    with open(json_file_path, "r") as json_file:
        dictionary = jsonref_loads(
            json_file.read(), base_uri=root_path.as_uri()
        )

    return dictionary


def load_configuration(configuration_file_path: str) -> dict:

    with open(configuration_file_path, "r") as configuration_file:

        return safe_load(configuration_file)


def validate_configuration(schema_path: Path, configuration: dict):

    schema_path = str(schema_path)

    if not exists(schema_path):
        raise Exception(f"{schema_path} does not exist")

    def retrieve_from_path(path: str):
        return Resource.from_contents(json_loads(Path(path).read_text()))

    Draft202012Validator(
        {"$ref": schema_path},
        registry=Registry(retrieve=retrieve_from_path)
    ).validate(configuration)


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

            optional_attributes = (
                all_attributes.difference(positional_attributes)
            )

            positional_attributes = sorted(list(positional_attributes))
            optional_attributes = sorted(list(optional_attributes))

            result_positional_attributes = OrderedDict()
            result_optional_attributes = OrderedDict()

            for positional_attribute in positional_attributes:

                result_positional_attributes[positional_attribute] = (
                    str(
                        _type_type[
                            schema_properties[positional_attribute]["type"]
                        ].__name__
                    )
                )

            for optional_attribute in optional_attributes:

                result_optional_attributes[optional_attribute] = (
                    str(
                        _type_type[
                            schema_properties[optional_attribute]["type"]
                        ].__name__
                    )
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
                "children": children
            }

            if recursive_path:
                return

            for (
                schema_properties_key,
                schema_properties_value
            ) in schema_properties.items():

                schema_properties_value_type = (
                    schema_properties_value.get("type")
                )

                if (
                    schema_properties_value_type != "object"
                    and schema_properties_value_type != "array"
                ):
                    continue

                if isinstance(schema_properties_value, JsonRef):
                    schema_properties_value_id = (
                        id(schema_properties_value.__subject__)
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
                        current_schema_value_id
                    ) in zip(
                        schema_key_stack[1:],
                        schema_value_id_stack
                    ):
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
            processed_schema_value
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
                "recursive_path": processed_schema_value["recursive_path"]
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
                    for line in environment.get_template("template.jinja2").
                    render(locals()).split("\n")
                ]
            )
        )


def create_object(
    configuration: dict, processed_schema: dict, object_name: str
) -> object:

    def create_object(
        configuration: dict,
        processed_schema: dict,
        path_function: dict,
        original_processed_schema: dict,
        original_path_function: dict,
    ) -> object:

        positional_arguments = []
        optional_arguments = {}

        for configuration_key, configuration_value in (
            configuration.items()
        ):

            if isinstance(configuration_value, dict):

                if processed_schema["recursive_path"]:

                    new_processed_schema = original_processed_schema
                    new_path_function = original_path_function

                    for path in processed_schema["recursive_path"]:
                        new_processed_schema = (
                            new_processed_schema[path]["children"]
                        )
                        new_path_function = (
                            new_path_function[path]["children"]
                        )

                    new_processed_schema = (
                        new_processed_schema[configuration_key]
                    )
                    new_path_function = (
                        new_path_function[configuration_key]
                    )
                else:
                    new_processed_schema = (
                        processed_schema["children"][configuration_key]
                    )
                    new_path_function = (
                        path_function["children"][configuration_key]
                    )

                object_ = create_object(
                    configuration_value,
                    new_processed_schema,
                    new_path_function,
                    original_processed_schema,
                    original_path_function,
                )

            elif isinstance(configuration_value, list):

                object_ = []

                for element in configuration_value:

                    object_.append(
                        create_object(
                            element,
                            processed_schema["children"][configuration_key],
                            path_function["children"][configuration_key],
                            original_processed_schema,
                            original_path_function,
                        )
                    )

            else:

                object_ = configuration_value

            if configuration_key in (
                processed_schema["positional_attributes"].keys()
            ):
                positional_arguments.append(object_)

            else:
                optional_arguments[configuration_key] = object_

        return path_function["function"](
            *positional_arguments, **optional_arguments
        )

    return create_object(
        configuration[object_name],
        processed_schema[object_name],
        path_function[object_name],
        processed_schema,
        path_function,
    )


def substitute_environment_variables(
    configuration: dict,
    processed_schema: dict
) -> dict:

    def traverse(
        configuration: dict,
        processed_schema: dict,
        original_processed_schema: dict
    ):

        for configuration_key, configuration_value in configuration.items():

            if configuration_key not in processed_schema.keys():
                continue

            if isinstance(configuration_value, dict):

                recursive_paths = (
                    processed_schema[configuration_key]["recursive_path"]
                )

                if recursive_paths:

                    children = original_processed_schema

                    for recursive_path in recursive_paths:
                        children = children[recursive_path]["children"]

                else:
                    children = processed_schema[configuration_key]["children"]

                traverse(
                    configuration_value,
                    children,
                    original_processed_schema
                )

            elif isinstance(configuration_value, list):

                for element in configuration_value:
                    if isinstance(element, dict):
                        traverse(
                            element,
                            processed_schema[configuration_key]["children"],
                            original_processed_schema
                        )

            elif isinstance(configuration_value, str):

                match = _environment_variable_regex.match(configuration_value)

                if match is not None:

                    configuration[configuration_key] = (
                        __builtins__[processed_schema[configuration_key]]
                        (environ.get(match.group(1)))
                    )

    traverse(configuration, processed_schema, processed_schema)

    return configuration
