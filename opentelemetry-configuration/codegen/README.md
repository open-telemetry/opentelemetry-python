# Code Generation Templates

Custom [datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator) templates used when generating `models.py` from the OpenTelemetry configuration JSON schema.

## `dataclass.jinja2`

Extends the default dataclass template to support `additionalProperties` from the JSON Schema. Schema types that allow additional properties (e.g. `Sampler`, `SpanExporter`, `TextMapPropagator`) get:

- `@_additional_properties` decorator: captures user-defined constructor kwargs
- `additional_properties: ClassVar[dict[str, Any]]` annotation: satisfies type checkers without creating a dataclass field

This enables plugin/custom component names to flow through typed dataclasses without a post-processing step.

Schema types that allow exactly one property (`minProperties: 1` and `maxProperties: 1`, e.g. `Sampler`, `SpanExporter`, `Aggregation`) get the `@_exactly_one_property` decorator, which raises `ValueError` at construction unless exactly one component choice (typed field or additional property) is set.

## `one_of_template_data.py`

datamodel-codegen does not expose `minProperties`/`maxProperties` to templates. This script derives an `exactly_one_property` flag for each such schema type and writes it as `--extra-template-data` for `dataclass.jinja2`.

## Usage

Templates are applied automatically when regenerating models:

```sh
tox -e generate-config-from-jsonschema
```

The template directory is configured in `pyproject.toml` under `[tool.datamodel-codegen]`.

See `opentelemetry-configuration/src/opentelemetry/configuration/README.md` for the full schema update workflow.
