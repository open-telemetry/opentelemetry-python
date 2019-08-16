# Contributing to opentelemetry-python

The Python special interest group (SIG) meets regularly. See the OpenTelemetry
[community](https://github.com/open-telemetry/community#python-sdk) repo for
information on this and other language SIGs.

See the [public meeting notes](https://docs.google.com/document/d/1CIMGoIOZ-c3-igzbd6_Pnxx1SjAkjwqoYSUWxPY8XIs/edit)
for a summary description of past meetings. To request edit access, join the
meeting or get in touch on [Gitter](https://gitter.im/open-telemetry/opentelemetry-python).

## Pull Request

### How to send PR

* Everyone can send PR.
* You need to fork the project in GitHub.

Clone the upstream repo:

```sh
$ git clone https://https://github.com/open-telemetry/opentelemetry-python.git
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

Checkout a new branch, make modifications and push the branch to your fork:

```sh
$ git checkout -b feature
# edit files
$ git commit
$ git push fork feature
```

Open a pull request against the main opentelemetry-python repo.

### How to Receive Comments

* If the PR is not ready for review, please put "[WIP]" in the title, or tag it
  as "work-in-progress", or mark it as "draft".
* Make sure CLA is signed and CI is clear.

### How to Get PR Merged

A PR is considered as **ready for merge** when:
* It got two approvals from Collaborators/Maintainers (at different companies).
* Major feedbacks should be resolved.
* The PR should stay at least one working day before getting merged, this
  gives people reasonable time to review.
* Trivial change (typo, cosmetic, doc, etc.) doesn't have to wait for one day.
* Urgent fix can take exception as long as it has been actively communicated.

Any Collaborator/Maintainer can merge the PR once it is **ready for merge**.

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

## Become a Collaborator

Collaborators have write access to the repo.

To become a Collaborator:
* Become an active Contributor by working on PRs.
* Actively participate in the community meeting, design discussion, PR review
   and issue discussion.
* Contact the Maintainers, express the willingness and commitment.
* Acknowledged and approved by two Maintainers (at different companies).

## Become a Maintainer

Maintainers have admin access to the repo.

To become a Maintainer:
* Become a [member of OpenTelemetry organization](https://github.com/orgs/open-telemetry/people).
* Become a Collaborator.
* Demonstrate the ability and commitment.
* Contact the Maintainers, express the willingness and commitment.
* Acknowledged and approved by all the current Maintainers.