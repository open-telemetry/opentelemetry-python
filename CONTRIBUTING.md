# Contributing to opentelemetry-python

The Python special interest group (SIG) meets regularly. See the OpenTelemetry
[community](https://github.com/open-telemetry/community#python-sdk) repo for
information on this and other language SIGs.

See the [public meeting notes](https://docs.google.com/document/d/1CIMGoIOZ-c3-igzbd6_Pnxx1SjAkjwqoYSUWxPY8XIs/edit)
for a summary description of past meetings. To request edit access join the
meeting or get in touch on Gitter.

## Running Tests

Execute tests as well as the linting process with tox:

    pip install --user tox
    tox  # execute in the root of the repository

## Testing

The standard Python unittest module is used to author unit tests.

## Design Choices

As with other OpenTelemetry clients, opentelemetry-python follows the 
[opentelemetry-specification](https://github.com/open-telemetry/opentelemetry-specification).

It's especially valuable to read through the [library guidelines](https://github.com/open-telemetry/opentelemetry-specification/blob/master/specification/library-guidelines.md).

### Focus on Capabilities, Not Structure Compliance

OpenTelemetry is an evolving specification, one where the desires and
use cases are clear, but the method to satisfy those uses cases are not.

As such, Contributions should provide functionality and behavior that 
conforms to the specification, but the interface and structure is flexible.

It is preferable to have contributions follow the idioms of the language 
rather than conform to specific API names or argument patterns in the spec.

For a deeper discussion, see: https://github.com/open-telemetry/opentelemetry-specification/issues/165


## Styleguide

* docstrings should adhere to the Google styleguide as specified
  with the [napolean extension](http://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html#google-vs-numpy) extension in [Sphinx](http://www.sphinx-doc.org/en/master/index.html).