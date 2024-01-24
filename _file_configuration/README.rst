OpenTelemetry Python File Configuration Prototype
=================================================

This component is EXPERIMENTAL and subject to any kind of change at any moment.

This prototype first needs the ``src/opentelemetry/file_configuration/_interna/path_function.py``
to be generated with the ``opentelemetry.file_configuration.render_schema`` function.

Once this file is generated, implement the functions defined there.

To create any provider object first create a ``Resource`` object:

.. code-block:: python

    from opentelemetry.file_configuration._internal.path_function import set_resource
    from opentelemetry.file_configuration import (
        resolve_schema,
        process_schema,
        create_object,
        validate_file_configuration,
    )
    from pathlib import Path

    data_path = Path(__file__).parent.joinpath("data")

    file_configuration = validate_file_configuration(
        data_path.joinpath("kitchen-sink.yaml")
    )

    processed_schema = process_schema(
        resolve_schema(
            data_path.joinpath("opentelemetry_file_configuration.json")
        )
    )

    set_resource(
        create_object(file_configuration, processed_schema, "resource")
    )

    tracer_provider = create_object(
        file_configuration, processed_schema, "tracer_provider"
    )

To run the tests, just run ``nox`` from the directory where ``noxfile.py`` is.
