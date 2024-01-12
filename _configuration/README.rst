OpenTelemetry Python Configuration Prototype
============================================

This component is EXPERIMENTAL and subject to any kind of change at any moment.

This prototype first needs the ``src/opentelemetry/configuration/_interna/path_function.py``
to be generated with the ``opentelemetry.configuration.render_schema`` function.

Once this file is generated, implement the functions defined there.

To create any provider object first create a ``Resource`` object:

.. code-block:: python

    from opentelemetry.configuration._internal.path_function import set_resource
    from opentelemetry.configuration import (
        resolve_schema,
        process_schema,
        create_object,
        validate_configuration,
    )
    from pathlib import Path

    data_path = Path(__file__).parent.joinpath("data")

    configuration = validate_configuration(
        data_path.joinpath("kitchen-sink.yaml")
    )

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
