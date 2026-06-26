# Code Generation Templates

Custom [datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator) templates used when generating `models.py` from the OpenTelemetry configuration JSON schema.

## `dataclass.jinja2`

Extends the default dataclass template to support `additionalProperties` from the JSON Schema. Schema types that allow additional properties (e.g. `Sampler`, `SpanExporter`, `TextMapPropagator`) get:

- `@_additional_properties` decorator — captures user-defined constructor kwargs
- `additional_properties` dataclass field with `init=False` and `default_factory=dict`

The generated field is not accepted as a constructor argument. The
`@_additional_properties` decorator assigns user-defined constructor kwargs to
the field during initialization, which keeps plugin/custom component names
flowing through typed dataclasses without a post-processing step.

## Usage

Templates are applied automatically when regenerating models:

```sh
tox -e generate-config-from-jsonschema
```

The template directory is configured in `pyproject.toml` under `[tool.datamodel-codegen]`.

See `opentelemetry-sdk/src/opentelemetry/sdk/_configuration/README.md` for the full schema update workflow.
