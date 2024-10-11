# Contributing to opentelemetry-python

The Python special interest group (SIG) meets weekly on Thursdays at 9AM PST. Check the [OpenTelemetry community calendar](https://calendar.google.com/calendar/embed?src=google.com_b79e3e90j7bbsa2n2p5an5lf60%40group.calendar.google.com) for specific dates and Zoom meeting links.

See the [public meeting notes](https://docs.google.com/document/d/1CIMGoIOZ-c3-igzbd6_Pnxx1SjAkjwqoYSUWxPY8XIs/edit)
for a summary description of past meetings.

See to the [community membership document](https://github.com/open-telemetry/community/blob/main/community-membership.md)
on how to become a [**Member**](https://github.com/open-telemetry/community/blob/main/community-membership.md#member),
[**Approver**](https://github.com/open-telemetry/community/blob/main/community-membership.md#approver)
and [**Maintainer**](https://github.com/open-telemetry/community/blob/main/community-membership.md#maintainer).

Before you can contribute, you will need to sign the [Contributor License Agreement](https://docs.linuxfoundation.org/lfx/easycla/contributors).

Please also read the [OpenTelemetry Contributor Guide](https://github.com/open-telemetry/community/blob/main/guides/contributor/README.md).

# Find your right repo

This is the main repo for OpenTelemetry Python. Nevertheless, there are other repos that are related to this project.
Please take a look at this list first, your contributions may belong in one of these repos better:

1. [OpenTelemetry Contrib](https://github.com/open-telemetry/opentelemetry-python-contrib): Instrumentations for third-party
   libraries and frameworks.

## Find a Buddy and get Started Quickly!

If you are looking for someone to help you find a starting point and be a resource for your first contribution, join our
Slack and find a buddy!

1. Join [Slack](https://slack.cncf.io/) and join our [channel](https://cloud-native.slack.com/archives/C01PD4HUVBL).
2. Post in the room with an introduction to yourself, what area you are interested in (check issues marked "Help Wanted"),
and say you are looking for a buddy. We will match you with someone who has experience in that area.

The Slack channel will be used for introductions and an entry point for external people to be triaged and redirected. For
discussions, please open up an issue or a Github [Discussion](https://github.com/open-telemetry/opentelemetry-python/discussions).

Your OpenTelemetry buddy is your resource to talk to directly on all aspects of contributing to OpenTelemetry: providing
context, reviewing PRs, and helping those get merged. Buddies will not be available 24/7, but is committed to responding
during their normal contribution hours.

## Development

This project uses [tox](https://tox.readthedocs.io) to automate
some aspects of development, including testing against multiple Python versions.
To install `tox`, run:

```console
$ pip install tox
```

You can run `tox` with the following arguments:

- `tox` to run all existing tox commands, including unit tests for all packages
  under multiple Python versions
- `tox -e docs` to regenerate the API docs
- `tox -e opentelemetry-api` and `tox -e opentelemetry-sdk` to run the API and SDK unit tests
- `tox -e py312-opentelemetry-api` to e.g. run the API unit tests under a specific
  Python version
- `tox -e spellcheck` to run a spellcheck on all the code
- `tox -e lint-some-package` to run lint checks on `some-package`

`black` and `isort` are executed when `tox -e lint` is run. The reported errors can be tedious to fix manually.
An easier way to do so is:

1. Run `.tox/lint/bin/black .`
2. Run `.tox/lint/bin/isort .`

Or you can call formatting and linting in one command by [pre-commit](https://pre-commit.com/):

```console
$ pre-commit
```

You can also configure it to run lint tools automatically before committing with:

```console
$ pre-commit install
```

We try to keep the amount of _public symbols_ in our code minimal. A public symbol is any Python identifier that does not start with an underscore.
Every public symbol is something that has to be kept in order to maintain backwards compatibility, so we try to have as few as possible.

To check if your PR is adding public symbols, run `tox -e public-symbols-check`. This will always fail if public symbols are being added/removed. The idea
behind this is that every PR that adds/removes public symbols fails in CI, forcing reviewers to check the symbols to make sure they are strictly necessary.
If after checking them, it is considered that they are indeed necessary, the PR will be labeled with `Approve Public API check` so that this check is not
run.

Also, we try to keep our console output as clean as possible. Most of the time this means catching expected log messages in the test cases:

``` python
from logging import WARNING

...

    def test_case(self):
        with self.assertLogs(level=WARNING):
            some_function_that_will_log_a_warning_message()
```

Other options can be to disable logging propagation or disabling a logger altogether.

A similar approach can be followed to catch warnings:

``` python
    def test_case(self):
        with self.assertWarns(DeprecationWarning):
            some_function_that_will_raise_a_deprecation_warning()
```

See
[`tox.ini`](https://github.com/open-telemetry/opentelemetry-python/blob/main/tox.ini)
for more detail on available tox commands.

#### Contrib repo

Some of the `tox` targets install packages from the [OpenTelemetry Python Contrib Repository](https://github.com/open-telemetry/opentelemetry-python.git) via
pip. The version of the packages installed defaults to the `main` branch in that repository when `tox` is run locally. It is possible to install packages tagged
with a specific git commit hash by setting an environment variable before running tox as per the following example:

```
CONTRIB_REPO_SHA=dde62cebffe519c35875af6d06fae053b3be65ec tox
```

The continuation integration overrides that environment variable with as per the configuration
[here](https://github.com/open-telemetry/opentelemetry-python/blob/main/.github/workflows/test_0.yml#L14).

### Benchmarks

Some packages have benchmark tests. To run them, run `tox -f benchmark`. Benchmark tests use `pytest-benchmark` and they output a table with results to the console.

To write benchmarks, simply use the [pytest benchmark fixture](https://pytest-benchmark.readthedocs.io/en/latest/usage.html#usage) like the following:

```python
def test_simple_start_span(benchmark):
    def benchmark_start_as_current_span(span_name, attribute_num):
        span = tracer.start_span(
            span_name,
            attributes={"count": attribute_num},
        )
        span.end()

    benchmark(benchmark_start_as_current_span, "benchmarkedSpan", 42)
```

Make sure the test file is under the `benchmarks/` folder of
the package it is benchmarking and further has a path that corresponds to the
file in the package it is testing. Make sure that the file name begins with
`test_benchmark_`. (e.g. `opentelemetry-sdk/benchmarks/trace/propagation/test_benchmark_b3_format.py`)

## Pull Requests

### How to Send Pull Requests

Everyone is welcome to contribute code to `opentelemetry-python` via GitHub
pull requests (PRs).

To create a new PR, fork the project in GitHub and clone the upstream repo:

```console
$ git clone https://github.com/open-telemetry/opentelemetry-python.git
$ cd opentelemetry-python
```

Add your fork as an origin:

```console
$ git remote add fork https://github.com/YOUR_GITHUB_USERNAME/opentelemetry-python.git
```

Run tests:

```sh
# make sure you have all supported versions of Python installed
$ pip install tox  # only first time.
$ tox  # execute in the root of the repository
```

Check out a new branch, make modifications and push the branch to your fork:

```sh
$ git checkout -b feature
# edit files
$ git commit
$ git push fork feature
```

Open a pull request against the main `opentelemetry-python` repo.

Pull requests are also tested for their compatibility with packages distributed
by OpenTelemetry in the [OpenTelemetry Python Contrib Repository](https://github.com/open-telemetry/opentelemetry-python.git).

If a pull request (PR) introduces a change that would break the compatibility of
these packages with the Core packages in this repo, a separate PR should be
opened in the Contrib repo with changes to make the packages compatible.

Follow these steps:
1. Open Core repo PR (Contrib Tests will fail)
2. Open Contrib repo PR and modify its `CORE_REPO_SHA` in `.github/workflows/test_x.yml`
to equal the commit SHA of the Core repo PR to pass tests
3. Modify the Core repo PR `CONTRIB_REPO_SHA` in `.github/workflows/test_x.yml` to
equal the commit SHA of the Contrib repo PR to pass Contrib repo tests (a sanity
check for the Maintainers & Approvers)
4. Merge the Contrib repo
5. Restore the Core repo PR `CONTRIB_REPO_SHA` to point to `main`
6. Merge the Core repo PR

### How to Receive Comments

* If the PR is not ready for review, please put `[WIP]` in the title, tag it
  as `work-in-progress`, or mark it as [`draft`](https://github.blog/2019-02-14-introducing-draft-pull-requests/).
* Make sure CLA is signed and CI is clear.

### How to Get PRs Merged

A PR is considered to be **ready to merge** when:
* It has received two approvals from [Approvers](https://github.com/open-telemetry/community/blob/main/community-membership.md#approver)
  / [Maintainers](https://github.com/open-telemetry/community/blob/main/community-membership.md#maintainer)
  (at different companies).
* Major feedbacks are resolved.
* All tests are passing, including Contrib Repo tests which may require
updating the GitHub workflow to reference a PR in the Contrib repo
* It has been open for review for at least one working day. This gives people
  reasonable time to review.
* Trivial change (typo, cosmetic, doc, etc.) doesn't have to wait for one day.
* Urgent fix can take exception as long as it has been actively communicated.

#### Allow edits from maintainers

Something _very important_ is to allow edits from maintainers when opening a PR. This will
allow maintainers to rebase your PR against `main` which is necessary in order to merge
your PR. You could do it yourself too, but keep in mind that every time another PR gets
merged, your PR will require rebasing. Since only maintainers can merge your PR it is
almost impossible for maintainers to find your PR just when it has been rebased by you so
that it can be merged. Allowing maintainers to edit your PR also allows them to help you
get your PR merged by making any minor fixes to solve any issue that while being unrelated
to your PR, can still happen.

#### Fork from a personal Github account

Right now Github [does not allow](https://github.com/orgs/community/discussions/5634) PRs
to be edited by maintainers if the corresponding repo fork exists in a Github organization.
Please for this repo in a personal Github account instead.

One of the maintainers will merge the PR once it is **ready to merge**.

## Design Choices

As with other OpenTelemetry clients, opentelemetry-python follows the
[opentelemetry-specification](https://github.com/open-telemetry/opentelemetry-specification).

It's especially valuable to read through the [library guidelines](https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/library-guidelines.md).

### Focus on Capabilities, Not Structure Compliance

OpenTelemetry is an evolving specification, one where the desires and
use cases are clear, but the method to satisfy those uses cases are not.

As such, contributions should provide functionality and behavior that
conforms to the specification, but the interface and structure is flexible.

It is preferable to have contributions follow the idioms of the language
rather than conform to specific API names or argument patterns in the spec.

For a deeper discussion, see: https://github.com/open-telemetry/opentelemetry-specification/issues/165

### Environment Variables

If you are adding a component that introduces new OpenTelemetry environment variables, put them all in a module,
as it is done in `opentelemetry.environment_variables` or in `opentelemetry.sdk.environment_variables`.

Keep in mind that any new environment variable must be declared in all caps and must start with `OTEL_PYTHON_`.

Register this module with the `opentelemetry_environment_variables` entry point to make your environment variables
automatically load as options for the `opentelemetry-instrument` command.

## Style Guide

* docstrings should adhere to the [Google Python Style
  Guide](http://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
  as specified with the [napoleon
  extension](http://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html#google-vs-numpy)
  extension in [Sphinx](http://www.sphinx-doc.org/en/master/index.html).

## Updating supported Python versions

### Bumping the Python baseline

When updating the minimum supported Python version remember to:

- Remove the version in `pyproject.toml` trove classifiers
- Remove the version from `tox.ini`
- Search for `sys.version_info` usage and remove code for unsupported versions
- Bump `py-version` in `.pylintrc` for Python version dependent checks

### Adding support for a new Python release

When adding support for a new Python release remember to:

- Add the version in `tox.ini`
- Add the version in `pyproject.toml` trove classifiers
- Update github workflows accordingly; lint and benchmarks use the latest supported version
- Update `.pre-commit-config.yaml`
- Update tox examples in the documentation

## Contributions that involve new packages

As part of an effort to mitigate namespace squatting on Pypi, please ensure to check whether a package name has been taken already on Pypi before contributing a new package. Contact a maintainer, bring the issue up in the weekly Python SIG or create a ticket in Pypi if a desired name has already been taken.
