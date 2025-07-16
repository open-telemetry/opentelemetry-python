# OpenTelemetry Python
[![Slack](https://img.shields.io/badge/slack-@cncf/otel/python-brightgreen.svg?logo=slack)](https://cloud-native.slack.com/archives/C01PD4HUVBL)
[![Build Status 0](https://github.com/open-telemetry/opentelemetry-python/actions/workflows/test_0.yml/badge.svg?branch=main)](https://github.com/open-telemetry/opentelemetry-python/actions/workflows/test_0.yml)
[![Build Status 1](https://github.com/open-telemetry/opentelemetry-python/actions/workflows/test_1.yml/badge.svg?branch=main)](https://github.com/open-telemetry/opentelemetry-python/actions/workflows/test_1.yml)
[![Minimum Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Release](https://img.shields.io/github/v/release/open-telemetry/opentelemetry-python?include_prereleases&style=)](https://github.com/open-telemetry/opentelemetry-python/releases/)
[![Read the Docs](https://readthedocs.org/projects/opentelemetry-python/badge/?version=latest)](https://opentelemetry-python.readthedocs.io/en/latest/)

## Project Status

See the [OpenTelemetry Instrumentation for Python](https://opentelemetry.io/docs/instrumentation/python/#status-and-releases).

| Signal  | Status       | Project |
| ------- | ------------ | ------- |
| Traces  | Stable       | N/A     |
| Metrics | Stable       | N/A     |
| Logs    | Experimental | N/A     |

Project versioning information and stability guarantees can be found [here](./rationale.md#versioning-and-releasing).

## Getting started

You can find the getting started guide for OpenTelemetry Python [here](https://opentelemetry.io/docs/instrumentation/python/getting-started/).

If you are looking for **examples** on how to use the OpenTelemetry API to
instrument your code manually, or how to set up the OpenTelemetry
Python SDK, see https://opentelemetry.io/docs/instrumentation/python/manual/.

## Python Version Support

This project ensures compatibility with the current supported versions of the Python. As new Python versions are released, support for them is added and
as old Python versions reach their end of life, support for them is removed.

We add support for new Python versions no later than 3 months after they become stable.

We remove support for old Python versions 6 months after they reach their [end of life](https://devguide.python.org/devcycle/#end-of-life-branches).


## Documentation

The online documentation is available at https://opentelemetry-python.readthedocs.io/.
To access the latest version of the documentation, see
https://opentelemetry-python.readthedocs.io/en/latest/.

## Install

This repository includes multiple installable packages. The `opentelemetry-api`
package includes abstract classes and no-op implementations that comprise the OpenTelemetry API following the
[OpenTelemetry specification](https://github.com/open-telemetry/opentelemetry-specification).
The `opentelemetry-sdk` package is the reference implementation of the API.

Libraries that produce telemetry data should only depend on `opentelemetry-api`,
and defer the choice of the SDK to the application developer. Applications may
depend on `opentelemetry-sdk` or another package that implements the API.

The API and SDK packages are available on the Python Package Index (PyPI). You can install them via `pip` with the following commands:

```sh
pip install opentelemetry-api
pip install opentelemetry-sdk
```

The
[`exporter/`](https://github.com/open-telemetry/opentelemetry-python/tree/main/exporter)
directory includes OpenTelemetry exporter packages. You can install the packages separately with the following command:

```sh
pip install opentelemetry-exporter-{exporter}
```

The
[`propagator/`](https://github.com/open-telemetry/opentelemetry-python/tree/main/propagator)
directory includes OpenTelemetry propagator packages. You can install the packages separately with the following command:

```sh
pip install opentelemetry-propagator-{propagator}
```

To install the development versions of these packages instead, clone or fork
this repository and perform an [editable
install](https://pip.pypa.io/en/stable/reference/pip_install/#editable-installs):

```sh
pip install -e ./opentelemetry-api -e ./opentelemetry-sdk -e ./opentelemetry-semantic-conventions
```

For additional exporter and instrumentation packages, see the 
[`opentelemetry-python-contrib`](https://github.com/open-telemetry/opentelemetry-python-contrib) repository.

## Contributing

For information about contributing to OpenTelemetry Python, see [CONTRIBUTING.md](CONTRIBUTING.md).

We meet weekly on Thursdays at 9AM PST. The meeting is subject to change depending on contributors' availability. Check the [OpenTelemetry community calendar](https://calendar.google.com/calendar/embed?src=c_2bf73e3b6b530da4babd444e72b76a6ad893a5c3f43cf40467abc7a9a897f977%40group.calendar.google.com) for specific dates and Zoom meeting links.

Meeting notes are available as a public [Google doc](https://docs.google.com/document/d/1CIMGoIOZ-c3-igzbd6_Pnxx1SjAkjwqoYSUWxPY8XIs/edit).

### Maintainers

- [Aaron Abbott](https://github.com/aabmass), Google
- [Diego Hurtado](https://github.com/ocelotl), Lightstep
- [Leighton Chen](https://github.com/lzchen), Microsoft
- [Riccardo Magliocchetti](https://github.com/xrmx), Elastic

For more information about the maintainer role, see the [community repository](https://github.com/open-telemetry/community/blob/main/guides/contributor/membership.md#maintainer).

### Approvers

- [Emídio Neto](https://github.com/emdneto), PicPay
- [Jeremy Voss](https://github.com/jeremydvoss), Microsoft
- [Owais Lone](https://github.com/owais), Splunk
- [Pablo Collins](https://github.com/pmcollins), Splunk
- [Shalev Roda](https://github.com/shalevr), Cisco
- [Srikanth Chekuri](https://github.com/srikanthccv), signoz.io
- [Tammy Baylis](https://github.com/tammy-baylis-swi), SolarWinds

For more information about the approver role, see the [community repository](https://github.com/open-telemetry/community/blob/main/guides/contributor/membership.md#approver).

### Emeritus Maintainers

- [Alex Boten](https://github.com/codeboten)
- [Chris Kleinknecht](https://github.com/c24t)
- [Owais Lone](https://github.com/owais)
- [Reiley Yang](https://github.com/reyang)
- [Srikanth Chekuri](https://github.com/srikanthccv)
- [Yusuke Tsutsumi](https://github.com/toumorokoshi)

For more information about the emeritus role, see the [community repository](https://github.com/open-telemetry/community/blob/main/guides/contributor/membership.md#emeritus-maintainerapprovertriager).

### Emeritus Approvers

- [Ashutosh Goel](https://github.com/ashu658)
- [Carlos Alberto Cortez](https://github.com/carlosalberto)
- [Christian Neumüller](https://github.com/Oberon00)
- [Héctor Hernández](https://github.com/hectorhdzg)
- [Mauricio Vásquez](https://github.com/mauriciovasquezbernal)
- [Nathaniel Ruiz Nowell](https://github.com/NathanielRN)
- [Nikolay Sokolik](https://github.com/oxeye-nikolay)
- [Sanket Mehta](https://github.com/sanketmehta28)
- [Tahir H. Butt](https://github.com/majorgreys)

For more information about the emeritus role, see the [community repository](https://github.com/open-telemetry/community/blob/main/guides/contributor/membership.md#emeritus-maintainerapprovertriager).

### Thanks to all of our contributors!

<a href="https://github.com/open-telemetry/opentelemetry-python/graphs/contributors">
  <img alt="Repo contributors" src="https://contrib.rocks/image?repo=open-telemetry/opentelemetry-python" />
</a>
