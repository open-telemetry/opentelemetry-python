# Release instructions

## Preparing a new major or minor release

* Run the [Prepare release branch workflow](https://github.com/open-telemetry/opentelemetry-python/actions/workflows/prepare-release-branch.yml).
  * Press the "Run workflow" button, and leave the default branch `main` selected.
    * If making a pre-release of stable components (e.g. release candidate),
      enter the pre-release version number, e.g. `1.9.0rc2`.
      (otherwise the workflow will pick up the version from `main` and just remove the `-dev` suffix).
  * Review and merge the two pull requests that it creates
    (one is targeted to the release branch and one is targeted to `main`).

## Preparing a new patch release

* Backport pull request(s) to the release branch.
  * Run the [Backport workflow](https://github.com/open-telemetry/opentelemetry-python/actions/workflows/backport.yml).
  * Press the "Run workflow" button, then select the release branch from the dropdown list,
    e.g. `release/v1.9.x`, then enter the pull request number that you want to backport,
    then click the "Run workflow" button below that.
  * Review and merge the backport pull request that it generates.
* Merge a pull request to the release branch updating the `CHANGELOG.md`.
  * The heading for the unreleased entries should be `## Unreleased`.
* Run the [Prepare patch release workflow](https://github.com/open-telemetry/opentelemetry-python/actions/workflows/prepare-patch-release.yml).
  * Press the "Run workflow" button, then select the release branch from the dropdown list,
    e.g. `release/v1.9.x`, and click the "Run workflow" button below that.
  * Review and merge the pull request that it creates for updating the version.

## Making the release

* Run the [Release workflow](https://github.com/open-telemetry/opentelemetry-python/actions/workflows/release.yml).
  * Press the "Run workflow" button, then select the release branch from the dropdown list,
    e.g. `release/v1.9.x`, and click the "Run workflow" button below that.
  * This workflow will publish the artifacts and publish a GitHub release with release notes based on the change log.
  * Review and merge the pull request that it creates for updating the change log in main
    (note that if this is not a patch release then the change log on main may already be up-to-date,
    in which case no pull request will be created).

## Notes about "pre-releases"

* Pre-release versions (e.g. `1.9.0rc2`) are supported, and will cause a "short-term" release branch
  to be created based on the full version name
  (e.g. `release/v1.9.0rc2-0.21b0` instead of a "long-term" release branch name like `release/v1.9.x-0.21bx`).
* Patch releases are not supported on short-term release branches.
* The stable version in `main` in this case will remain the same (e.g. `1.9.0-dev`), since the next release version
  (that is not a prereleaes) is still `1.9.0`.
* The unstable version in `main` will be bumped  (e.g. `0.22b0-dev`).
* Note that the workflow does not support the concept of a pre-release for unstable artifacts.

## After the release

* Check PyPI
  * This should be handled automatically on release by the [publish action](https://github.com/open-telemetry/opentelemetry-python/blob/main/.github/workflows/publish.yml).
  * Check the [action logs](https://github.com/open-telemetry/opentelemetry-python/actions?query=workflow%3APublish) to make sure packages have been uploaded to PyPI
  * Check the release history (e.g. https://pypi.org/project/opentelemetry-api/#history) on PyPI
  * If for some reason the action failed, see [Publish failed](#publish-failed) below
* Move stable tag
  * Run the following (TODO automate):
    ```bash
    git tag -d stable
    git tag stable
    git push --delete origin tagname
    git push origin stable
    ```
  * This will ensure the docs are pointing at the stable release.
  * To validate this worked, ensure the stable build has run successfully:
    https://readthedocs.org/projects/opentelemetry-python/builds/.
    If the build has not run automatically, it can be manually trigger via the readthedocs interface.

## Troubleshooting

### Publish failed

If for some reason the action failed, do it manually:

- Switch to the release branch (important so we don't publish packages with "dev" versions)
- Build distributions with `./scripts/build.sh`
- Delete distributions we don't want to push (e.g. `testutil`)
- Push to PyPI as `twine upload --skip-existing --verbose dist/*`
- Double check PyPI!
