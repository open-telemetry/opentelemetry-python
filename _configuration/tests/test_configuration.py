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

from os import environ
from pathlib import Path
from unittest.mock import patch

from ipdb import set_trace
from jsonschema.validators import Draft202012Validator
from pytest import fail

from opentelemetry.configuration import (
    create_object,
    load_configuration,
    process_schema,
    render_schema,
    resolve_schema,
    substitute_environment_variables,
    validate_configuration,
)
from opentelemetry.configuration._internal.path_function import set_resource

set_trace

data_path = Path(__file__).parent.joinpath("data")


def test_create_object():

    configuration = load_configuration(
        data_path.joinpath("configuration").joinpath("configuration_0.yaml")
    )

    schema_path = data_path.joinpath("schema").joinpath(
        "opentelemetry_configuration.json"
    )

    try:
        validate_configuration(schema_path, configuration)
    except Exception as error:
        fail(f"Unexpected exception raised: {error}")

    processed_schema = process_schema(resolve_schema(schema_path))

    set_resource(create_object(configuration, processed_schema, "resource"))

    tracer_provider = create_object(
        configuration, processed_schema, "tracer_provider"
    )

    assert (
        tracer_provider.sampler.parent_based.root.trace_id_ratio_based._root._rate
    ) == 0.0001

    assert (
        tracer_provider.sampler.parent_based.local_parent_not_sampled.parent_based.remote_parent_not_sampled.trace_id_ratio_based._root._rate
    ) == 0.0001

    assert (tracer_provider._span_limits.max_events) == 128

    assert (
        tracer_provider._active_span_processor._span_processors[
            0
        ].max_queue_size
    ) == 2048

    assert (
        tracer_provider._active_span_processor._span_processors[
            0
        ].span_exporter._headers["api-key"]
    ) == "1234"

    assert (
        tracer_provider._active_span_processor._span_processors[
            1
        ].span_exporter.endpoint
    ) == "http://localhost:9411/api/v2/spans"

    assert (
        tracer_provider._active_span_processor._span_processors[
            2
        ].span_exporter.__class__.__name__
    ) == "ConsoleSpanExporter"

    assert (
        tracer_provider._resource._schema_url
    ) == "https://opentelemetry.io/schemas/1.16.0"


@patch.dict(environ, {"OTEL_BLRB_EXPORT_TIMEOUT": "943"}, clear=True)
def test_substitute_environment_variables():
    configuration = load_configuration(
        data_path.joinpath("configuration").joinpath("configuration_1.yaml")
    )

    schema_path = data_path.joinpath("schema").joinpath(
        "opentelemetry_configuration.json"
    )

    processed_schema = process_schema(resolve_schema(schema_path))
    configuration = substitute_environment_variables(
        configuration, processed_schema
    )

    assert (
        configuration["logger_provider"]["processors"][0]["batch"][
            "export_timeout"
        ]
    ) == 943
    try:
        validate_configuration(schema_path, configuration)
    except Exception as error:
        fail(f"Unexpected exception raised: {error}")


def test_render(tmpdir):

    try:
        render_schema(
            process_schema(
                resolve_schema(
                    data_path.joinpath("schema").joinpath(
                        "opentelemetry_configuration.json"
                    )
                )
            ),
            tmpdir.join("path_function.py"),
        )
    except Exception as error:
        fail(f"Unexpected exception raised: {error}")


def test_subschemas():

    schema_path = data_path.joinpath("schema").joinpath(
        "opentelemetry_configuration.json"
    )
    resolved_schema = resolve_schema(schema_path)
    resolved_schema

    # FIXME once the schema has been resolved, we get a dictionary. Add to this
    # dictionary the schema components of each plugin component sub schema then
    # use the resulting schema dictionary to do the validation.

    configuration = load_configuration(
        data_path.joinpath("configuration").joinpath("configuration_0.yaml")
    )

    # FIXME do the same for configuration components

    Draft202012Validator(resolved_schema).validate(configuration)


def test_dry_run():

    configuration = load_configuration(
        data_path.joinpath("configuration").joinpath("configuration_0.yaml")
    )

    schema_path = data_path.joinpath("schema").joinpath(
        "opentelemetry_configuration.json"
    )

    try:
        validate_configuration(schema_path, configuration)
    except Exception as error:
        fail(f"Unexpected exception raised: {error}")

    processed_schema = process_schema(resolve_schema(schema_path))

    result = create_object(
        configuration, processed_schema, "resource", dry_run=True
    )
    print()
    print(result)
