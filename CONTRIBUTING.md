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

## Development

This project uses [`tox`](https://tox.readthedocs.io) to automate some aspects
of development, including testing against multiple Python versions.

You can run:

- `tox` to run all existing tox commands, including unit tests for all packages
  under multiple Python versions
- `tox -e docs` to regenerate the API docs
- `tox -e test-api` and `tox -e test-sdk` to run the API and SDK unit tests
- `tox -e py37-test-api` to e.g. run the the API unit tests under a specific
  Python version
- `tox -e lint` to run lint checks on all code

See
[`tox.ini`](https://github.com/open-telemetry/opentelemetry-python/blob/master/tox.ini)
for more detail on available tox commands.

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

As such, Contributions should provide functionality and behavior that 
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
