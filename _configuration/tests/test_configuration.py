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

from opentelemetry.configuration._internal.path_function import set_resource
from opentelemetry.configuration import (
    resolve_schema,
    process_schema,
    create_object,
    validate_configuration,
    load_configuration,
    substitute_environment_variables,
    render_schema,
)
from unittest.mock import patch
from os import environ
from pathlib import Path
from pytest import fail

data_path = Path(__file__).parent.joinpath("data")


def test_create_object():

    configuration = load_configuration(
        data_path.joinpath("configuration_0.yaml")
    )

    try:
        validate_configuration(configuration)
    except Exception as error:
        fail(f"Unexpected exception raised: {error}")

    processed_schema = process_schema(
        resolve_schema(
            data_path.joinpath("opentelemetry_configuration.json")
        )
    )

    set_resource(
        create_object(configuration, processed_schema, "resource")
    )

    tracer_provider = create_object(
        configuration, processed_schema, "tracer_provider"
    )

    assert (
        tracer_provider.
        sampler.
        parent_based.
        root.
        trace_id_ratio_based.
        _root.
        _rate
    ) == 0.0001

    assert (
        tracer_provider.
        sampler.
        parent_based.
        local_parent_not_sampled.
        parent_based.
        remote_parent_not_sampled.
        trace_id_ratio_based.
        _root.
        _rate
    ) == 0.0001

    assert (
        tracer_provider.
        _span_limits.
        max_events
    ) == 128

    assert (
        tracer_provider.
        _active_span_processor.
        _span_processors[0].
        max_queue_size
    ) == 2048

    assert (
        tracer_provider.
        _active_span_processor.
        _span_processors[0].
        span_exporter.
        _headers["api-key"]
    ) == "1234"

    assert (
        tracer_provider.
        _active_span_processor.
        _span_processors[1].
        span_exporter.
        endpoint
    ) == "http://localhost:9411/api/v2/spans"

    assert (
        tracer_provider.
        _active_span_processor.
        _span_processors[2].
        span_exporter.
        __class__.
        __name__
    ) == "ConsoleSpanExporter"

    assert (
        tracer_provider.
        _resource.
        _schema_url
    ) == "https://opentelemetry.io/schemas/1.16.0"


@patch.dict(environ, {"OTEL_BLRB_EXPORT_TIMEOUT": "943"}, clear=True)
def test_substitute_environment_variables():
    configuration = load_configuration(
        data_path.joinpath("configuration_1.yaml")
    )

    processed_schema = process_schema(
        resolve_schema(
            data_path.joinpath("opentelemetry_configuration.json")
        )
    )
    configuration = substitute_environment_variables(
        configuration, processed_schema
    )

    assert (
        configuration
        ["logger_provider"]
        ["processors"]
        [0]
        ["batch"]
        ["export_timeout"]
    ) == 943
    try:
        validate_configuration(configuration)
    except Exception as error:
        fail(f"Unexpected exception raised: {error}")


def test_render(tmpdir):

    render_schema(
        process_schema(
            resolve_schema(
                data_path.joinpath("opentelemetry_configuration.json")
            )
        ),
        tmpdir.join("path_function.py")
    )
