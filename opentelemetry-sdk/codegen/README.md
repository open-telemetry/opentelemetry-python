# Code Generation Templates

Custom [datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator) templates used when generating `models.py` from the OpenTelemetry configuration JSON schema.

## `dataclass.jinja2`

Extends the default dataclass template to support `additionalProperties` from the JSON Schema. Schema types that allow additional properties (e.g. `Sampler`, `SpanExporter`, `TextMapPropagator`) get:

- `@_additional_properties_support` decorator — captures unknown constructor kwargs
- `additional_properties: ClassVar[dict[str, Any]]` annotation — satisfies type checkers without creating a dataclass field

This enables plugin/custom component names to flow through typed dataclasses without a post-processing step.

## Usage

Templates are applied automatically when regenerating models:

```sh
tox -e generate-config-from-jsonschema
```

The template directory is configured in `pyproject.toml` under `[tool.datamodel-codegen]`.

See `opentelemetry-sdk/src/opentelemetry/sdk/_configuration/README.md` for the full schema update workflow.
