# Contributing to opentelemetry-python

The Python special interest group (SIG) meets regularly. See the OpenTelemetry
[community](https://github.com/open-telemetry/community#python-sdk) repo for
information on this and other language SIGs.

See the [public meeting notes](https://docs.google.com/document/d/1CIMGoIOZ-c3-igzbd6_Pnxx1SjAkjwqoYSUWxPY8XIs/edit)
for a summary description of past meetings. To request edit access, join the
meeting or get in touch on [Gitter](https://gitter.im/open-telemetry/opentelemetry-python).

See to the [community membership document](https://github.com/open-telemetry/community/blob/master/community-membership.md)
on how to become a [**Member**](https://github.com/open-telemetry/community/blob/master/community-membership.md#member),
[**Approver**](https://github.com/open-telemetry/community/blob/master/community-membership.md#approver)
and [**Maintainer**](https://github.com/open-telemetry/community/blob/master/community-membership.md#maintainer).

# Find your right repo

This is the main repo for OpenTelemetry Python. Nevertheless, there are other repos that are related to this project.
Please take a look at this list first, your contributions may belong in one of these repos better:

1. [OpenTelemetry Contrib](https://github.com/open-telemetry/opentelemetry-python-contrib): Instrumentations for third-party
   libraries and frameworks. There is an ongoing effort to migrate into the Opentelemetry Contrib repo some of the existing
   programmatic instrumentations that are now in the `ext` directory in the main OpenTelemetry repo. Please ask in the Gitter
   channel (see below) for guidance if you want to contribute with these instrumentations.

## Find a Buddy and get Started Quickly!

If you are looking for someone to help you find a starting point and be a resource for your first contribution, join our
Gitter and find a buddy!

1. Join [Gitter.im](https://gitter.im) and join our [chat room](https://gitter.im/open-telemetry/opentelemetry-python).
2. Post in the room with an introduction to yourself, what area you are interested in (check issues marked "Help Wanted"),
and say you are looking for a buddy. We will match you with someone who has experience in that area.

Your OpenTelemetry buddy is your resource to talk to directly on all aspects of contributing to OpenTelemetry: providing
context, reviewing PRs, and helping those get merged. Buddies will not be available 24/7, but is committed to responding
during their normal contribution hours.

## Development

To quickly get up and running, you can use the `scripts/eachdist.py` tool that
ships with this project. First create a virtualenv and activate it.
Then run `python scripts/eachdist.py develop` to install all required packages
as well as the project's packages themselves (in `--editable` mode).

Further, you'll want to clone the Contrib repo locally to resolve paths needed
to run tests. `git clone git@github.com:open-telemetry/opentelemetry-python-contrib.git opentelemetry-python-contrib`.

You can then run `scripts/eachdist.py test` to test everything or
`scripts/eachdist.py lint` to lint everything (fixing anything that is auto-fixable).

Additionally, this project uses [`tox`](https://tox.readthedocs.io) to automate some aspects
of development, including testing against multiple Python versions.

You can run:

- `tox` to run all existing tox commands, including unit tests for all packages
  under multiple Python versions
- `tox -e docs` to regenerate the API docs
- `tox -e test-core-api` and `tox -e test-core-sdk` to run the API and SDK unit tests
- `tox -e py37-test-core-api` to e.g. run the API unit tests under a specific
  Python version
- `tox -e lint` to run lint checks on all code

See
[`tox.ini`](https://github.com/open-telemetry/opentelemetry-python/blob/master/tox.ini)
for more detail on available tox commands.

### Benchmarks

Performance progression of benchmarks for packages distributed by OpenTelemetry Python can be viewed as a [graph of throughput vs commit history](https://opentelemetry-python.readthedocs.io/en/latest/benchmarks/index.html). From this page, you can download a JSON file with the performance results.

Running the `tox` tests also runs the performance tests if any are available. Benchmarking tests are done with `pytest-benchmark` and they output a table with results to the console.

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

Make sure the test file is under the `tests/performance/benchmarks/` folder of
the package it is benchmarking and further has a path that corresponds to the
file in the package it is testing. Make sure that the file name begins with
`test_benchmark_`. (e.g. `opentelemetry-sdk/tests/performance/benchmarks/trace/propagation/test_benchmark_b3_format.py`)

## Pull Requests

### How to Send Pull Requests

Everyone is welcome to contribute code to `opentelemetry-python` via GitHub
pull requests (PRs).

To create a new PR, fork the project in GitHub and clone the upstream repo:

```sh
$ git clone https://github.com/open-telemetry/opentelemetry-python.git
```

Add your fork as an origin:

```sh
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
2. Open Contrib repo PR and modify its `CORE_REPO_SHA` in `.github/workflows/test.yml`
to equal the commit SHA of the Core repo PR to pass tests
3. Modify the Core repo PR `CONTRIB_REPO_SHA` in `.github/workflows/test.yml` to
equal the commit SHA of the Contrib repo PR to pass Contrib repo tests (a sanity
check for the Maintainers & Approvers)
4. Merge the Contrib repo
5. Restore the Core repo PR `CONTRIB_REPO_SHA` to point to `master`
6. Merge the Core repo PR

### How to Receive Comments

* If the PR is not ready for review, please put `[WIP]` in the title, tag it
  as `work-in-progress`, or mark it as [`draft`](https://github.blog/2019-02-14-introducing-draft-pull-requests/).
* Make sure CLA is signed and CI is clear.

### How to Get PRs Merged

A PR is considered to be **ready to merge** when:
* It has received two approvals from [Approvers](https://github.com/open-telemetry/community/blob/master/community-membership.md#approver)
  / [Maintainers](https://github.com/open-telemetry/community/blob/master/community-membership.md#maintainer)
  (at different companies).
* Major feedbacks are resolved.
* All tests are passing, including Contrib Repo tests which may require
updating the GitHub workflow to reference a PR in the Contrib repo
* It has been open for review for at least one working day. This gives people
  reasonable time to review.
* Trivial change (typo, cosmetic, doc, etc.) doesn't have to wait for one day.
* Urgent fix can take exception as long as it has been actively communicated.

Any Approver / Maintainer can merge the PR once it is **ready to merge**.

## Design Choices

As with other OpenTelemetry clients, opentelemetry-python follows the 
[opentelemetry-specification](https://github.com/open-telemetry/opentelemetry-specification).

It's especially valuable to read through the [library guidelines](https://github.com/open-telemetry/opentelemetry-specification/blob/master/specification/library-guidelines.md).

### Focus on Capabilities, Not Structure Compliance

OpenTelemetry is an evolving specification, one where the desires and
use cases are clear, but the method to satisfy those uses cases are not.

As such, contributions should provide functionality and behavior that
conforms to the specification, but the interface and structure is flexible.

It is preferable to have contributions follow the idioms of the language 
rather than conform to specific API names or argument patterns in the spec.

For a deeper discussion, see: https://github.com/open-telemetry/opentelemetry-specification/issues/165

## Style Guide

* docstrings should adhere to the [Google Python Style
  Guide](http://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
  as specified with the [napolean
  extension](http://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html#google-vs-numpy)
  extension in [Sphinx](http://www.sphinx-doc.org/en/master/index.html).
