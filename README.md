## OpenTelemetry Python
---
<p align="center">
  <strong>
    <a href="https://opentelemetry.io/docs/instrumentation/python/getting-started/">Getting Started<a/>
    &nbsp;&nbsp;&bull;&nbsp;&nbsp;
    <a href="https://opentelemetry-python.readthedocs.io/">API Documentation<a/>
    &nbsp;&nbsp;&bull;&nbsp;&nbsp;
    <a href="https://github.com/open-telemetry/opentelemetry-python/discussions">Getting In Touch (GitHub Discussions)<a/>
  </strong>
</p>

<p align="center">
  <a href="https://github.com/open-telemetry/opentelemetry-python/releases">
    <img alt="GitHub release (latest by date including pre-releases)" src="https://img.shields.io/github/v/release/open-telemetry/opentelemetry-python?include_prereleases&style=for-the-badge">
  </a>
  <a href="https://codecov.io/gh/open-telemetry/opentelemetry-python/branch/main/">
    <img alt="Codecov Status" src="https://img.shields.io/codecov/c/github/open-telemetry/opentelemetry-python?style=for-the-badge">
  </a>
  <a href="https://github.com/open-telemetry/opentelemetry-python/blob/main/LICENSE">
    <img alt="license" src="https://img.shields.io/badge/license-Apache_2.0-green.svg?style=for-the-badge">
  </a>
  <br/>
  <a href="https://github.com/open-telemetry/opentelemetry-python/actions?query=workflow%3ATest+branch%3Amaster">
    <img alt="Build Status" src="https://github.com/open-telemetry/opentelemetry-python/workflows/Test/badge.svg">
  </a>
  <img alt="Beta" src="https://img.shields.io/badge/status-beta-informational?logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAAAXNSR0IArs4c6QAAAIRlWElmTU0AKgAAAAgABQESAAMAAAABAAEAAAEaAAUAAAABAAAASgEbAAUAAAABAAAAUgEoAAMAAAABAAIAAIdpAAQAAAABAAAAWgAAAAAAAACQAAAAAQAAAJAAAAABAAOgAQADAAAAAQABAACgAgAEAAAAAQAAABigAwAEAAAAAQAAABgAAAAA8A2UOAAAAAlwSFlzAAAWJQAAFiUBSVIk8AAAAVlpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IlhNUCBDb3JlIDUuNC4wIj4KICAgPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4KICAgICAgPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIKICAgICAgICAgICAgeG1sbnM6dGlmZj0iaHR0cDovL25zLmFkb2JlLmNvbS90aWZmLzEuMC8iPgogICAgICAgICA8dGlmZjpPcmllbnRhdGlvbj4xPC90aWZmOk9yaWVudGF0aW9uPgogICAgICA8L3JkZjpEZXNjcmlwdGlvbj4KICAgPC9yZGY6UkRGPgo8L3g6eG1wbWV0YT4KTMInWQAABK5JREFUSA2dVm1sFEUYfmd2b/f2Pkqghn5eEQWKrRgjpkYgpoRCLC0oxV5apAiGUDEpJvwxEQ2raWPU+Kf8INU/RtEedwTCR9tYPloxGNJYTTQUwYqJ1aNpaLH3sXu3t7vjvFevpSqt7eSyM+/czvM8877PzB3APBoLgoDLsNePF56LBwqa07EKlDGg84CcWsI4CEbhNnDpAd951lXE2NkiNknCCTLv4HtzZuvPm1C/IKv4oDNXqNDHragety2XVzjECZsJARuBMyRzJrh1O0gQwLXuxofxsPSj4hG8fMLQo7bl9JJD8XZfC1E5yWFOMtd07dvX5kDwg6+2++Chq8txHGtfPoAp0gOFmhYoNFkHjn2TNUmrwRdna7W1QSkU8hvbGk4uThLrapaiLA2E6QY4u/lS9ItHfvJkxYsTMVtnAJLipYIWtVrcdX+8+b8IVnPl/R81prbuPZ1jpYw+0aEUGSkdFsgyBIaFTXCm6nyaxMtJ4n+TeDhJzGqZtQZcuYDgqDwDbqb0JF9oRpIG1Oea3bC1Y6N3x/WV8Zh83emhCs++hlaghDw+8w5UlYKq2lU7Pl8IkvS9KDqXmKmEwdMppVPKwGSEilmyAwJhRwWcq7wYC6z4wZ1rrEoMWxecdOjZWXeAQClBcYDN3NwVwD9pGwqUSyQgclcmxpNJqCuwLmDh3WtvPqXdlt+6Oz70HPGDNSNBee/EOen+rGbEFqDENBPDbtdCp0ukPANmzO0QQJYUpyS5IJJI3Hqt4maS+EB3199ozm8EDU/6fVNU2dQpdx3ZnKzeFXyaUTiasEV/gZMzJMjr3Z+WvAdQ+hs/zw9savimxUntDSaBdZ2f+Idbm1rlNY8esFffBit9HtK5/MejsrJVxikOXlb1Ukir2X+Rbdkd1KG2Ixfn2Ql4JRmELnYK9mEM8G36fAA3xEQ89fxXihC8q+sAKi9jhHxNqagY2hiaYgRCm0f0QP7H4Fp11LSXiuBY2aYFlh0DeDIVVFUJQn5rCnpiNI2gvLxHnASn9DIVHJJlm5rXvQAGEo4zvKq2w5G1NxENN7jrft1oxMdekETjxdH2Z3x+VTVYsPb+O0C/9/auN6v2hNZw5b2UOmSbG5/rkC3LBA+1PdxFxORjxpQ81GcxKc+ybVjEBvUJvaGJ7p7n5A5KSwe4AzkasA+crmzFtowoIVTiLjANm8GDsrWW35ScI3JY8Urv83tnkF8JR0yLvEt2hO/0qNyy3Jb3YKeHeHeLeOuVLRpNF+pkf85OW7/zJxWdXsbsKBUk2TC0BCPwMq5Q/CPvaJFkNS/1l1qUPe+uH3oD59erYGI/Y4sce6KaXYElAIOLt+0O3t2+/xJDF1XvOlWGC1W1B8VMszbGfOvT5qaRRAIFK3BCO164nZ0uYLH2YjNN8thXS2v2BK9gTfD7jHVxzHr4roOlEvYYz9QIz+Vl/sLDXInsctFsXjqIRnO2ZO387lxmIboLDZCJ59KLFliNIgh9ipt6tLg9SihpRPDO1ia5byw7de1aCQmF5geOQtK509rzfdwxaKOIq+73AvwCC5/5fcV4vo3+3LpMdtWHh0ywsJC/ZGoCb8/9D8F/ifgLLl8S8QWfU8cAAAAASUVORK5CYII=">
</p>

<p align="center">
  <strong>
    <a href="CONTRIBUTING.md">Contributing<a/>
    &nbsp;&nbsp;&bull;&nbsp;&nbsp;
    <a href="https://opentelemetry-python.readthedocs.io/en/stable/#examples">Examples<a/>
  </strong>
</p>

---

This page describes the Python [OpenTelemetry](https://opentelemetry.io/) implementation. OpenTelemetry is an observability framework for cloud-native software.

## Requirements
Unless otherwise noted, all published artifacts support Python 3.6 or higher. See CONTRIBUTING.md for additional instructions for building this project for development.

## Getting started

The goal of OpenTelemetry is to provide a single set of APIs to capture distributed traces and metrics from your application and send them to an observability platform. This project lets you do just that for applications written in Python.

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
pip install -e ./opentelemetry-api
pip install -e ./opentelemetry-sdk
pip install -e ./instrumentation/opentelemetry-instrumentation-{instrumentation}
```

For additional exporter and instrumentation packages, see the 
[`opentelemetry-python-contrib`](https://github.com/open-telemetry/opentelemetry-python-contrib) repository.

## Running Performance Tests

This section provides details on how to reproduce performance tests results on your own
machine.

### Resource Usage Tests

1. Install scalene using the following command

```sh
pip install scalene
```

2. Run the `scalene` tests on any of the example Python programs

```sh
scalene opentelemetry-<PACKAGE>/tests/performance/resource-usage/<PATH_TO_TEST>/profile_resource_usage_<NAME_OF_TEST>.py
```

## Python Version Support Addition and Removal

This project supports the latest Python versions. As new Python versions are released, support for them is added and
as old Python versions reach their end of life, support for them is removed.

We add support for new Python versions no later than 3 months after they become stable.

We remove support for old Python versions 6 months after they reach their [end of life](https://devguide.python.org/devcycle/#end-of-life-branches).

## Documentation

The online documentation is available at https://opentelemetry-python.readthedocs.io/.
To access the latest version of the documentation, see
https://opentelemetry-python.readthedocs.io/en/latest/.

## Contributing

For information about contributing to OpenTelemetry Python, see [CONTRIBUTING.md](CONTRIBUTING.md).

We meet weekly on Thursdays at 9AM PST. The meeting is subject to change depending on contributors' availability. Check the [OpenTelemetry community calendar](https://calendar.google.com/calendar/embed?src=google.com_b79e3e90j7bbsa2n2p5an5lf60%40group.calendar.google.com) for specific dates and Zoom meeting links.

Meeting notes are available as a public [Google doc](https://docs.google.com/document/d/1CIMGoIOZ-c3-igzbd6_Pnxx1SjAkjwqoYSUWxPY8XIs/edit). For edit access, get in touch on [GitHub Discussions](https://github.com/open-telemetry/opentelemetry-python/discussions).

Approvers ([@open-telemetry/python-approvers](https://github.com/orgs/open-telemetry/teams/python-approvers)):

- [Aaron Abbott](https://github.com/aabmass), Google
- [Alex Boten](https://github.com/codeboten), Lightstep
- [Owais Lone](https://github.com/owais), Splunk
- [Nathaniel Ruiz Nowell](https://github.com/NathanielRN), AWS

*For more information about the approver role, see the [community repository](https://github.com/open-telemetry/community/blob/main/community-membership.md#approver).*

Maintainers ([@open-telemetry/python-maintainers](https://github.com/orgs/open-telemetry/teams/python-maintainers)):

- [Diego Hurtado](https://github.com/ocelotl), Lightstep
- [Leighton Chen](https://github.com/lzchen), Microsoft
- [Srikanth Chekuri](https://github.com/srikanthccv)

*For more information about the maintainer role, see the [community repository](https://github.com/open-telemetry/community/blob/main/community-membership.md#maintainer).*

### Thanks to all the people who already contributed!

<a href="https://github.com/open-telemetry/opentelemetry-python/graphs/contributors">
  <img src="https://contributors-img.web.app/image?repo=open-telemetry/opentelemetry-python" />
</a>

## Project Status

For project boards and milestones, see the following links: 
- [Project boards](https://github.com/open-telemetry/opentelemetry-python/projects)
- [Milestones](https://github.com/open-telemetry/opentelemetry-python/milestones)

We try to keep these links accurate, so they're the best place to go for questions about project status. The dates and features described in the issues
and milestones are estimates and subject to change.
