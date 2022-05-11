# Release instructions

## Preparing a new major or minor release

* Merge a pull request to `main` updating the `CHANGELOG.md`.
  * The heading for the release should include the release version but not the release date, e.g.
    `## Version 1.9.0 (unreleased)`.
* Run the [Prepare release branch workflow](https://github.com/open-telemetry/opentelemetry-python/actions/workflows/prepare-release-branch.yml).
  * Press the "Run workflow" button, and leave the default branch `main` selected.
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
  * The heading for the release should include the release version but not the release date, e.g.
    `## Version 1.9.1 (Unreleased)`.
* Run the [Prepare patch release workflow](https://github.com/open-telemetry/opentelemetry-python/actions/workflows/prepare-patch-release.yml).
  * Press the "Run workflow" button, then select the release branch from the dropdown list,
    e.g. `release/v1.9.x`, and click the "Run workflow" button below that.
* Review and merge the pull request that it creates.

## Making the release

Run the [Release workflow](https://github.com/open-telemetry/opentelemetry-python/actions/workflows/release.yml).

* Press the "Run workflow" button, then select the release branch from the dropdown list,
  e.g. `release/v1.9.x`, and click the "Run workflow" button below that.
* This workflow will publish the artifacts and publish a GitHub release with release notes based on the change log.
* Review and merge the pull request that the release workflow creates against the release branch
  which adds the release date to the change log.

## After the release

Run the [Merge change log to main workflow](https://github.com/open-telemetry/opentelemetry-python/actions/workflows/merge-change-log-to-main.yml).

* Press the "Run workflow" button, then select the release branch from the dropdown list,
  e.g. `release/v1.9.x`, and click the "Run workflow" button below that.
* This will create a pull request that merges the change log updates from the release branch
  back to `main`.
* Review and merge the pull request that it creates.
* This workflow will fail if there have been conflicting change log updates introduced in `main`,
  in which case you will need to merge the change log updates manually and send your own pull
  request against `main`.


Release Process:
- [Check PyPI](#Check-PyPI)
- [Move stable tag](#Move-stable-tag)
- [Update main](#Update-main)
- [Troubleshooting](#troubleshooting)

## Check PyPI

This should be handled automatically on release by the [publish action](https://github.com/open-telemetry/opentelemetry-python/blob/main/.github/workflows/publish.yml).

- Check the [action logs](https://github.com/open-telemetry/opentelemetry-python/actions?query=workflow%3APublish) to make sure packages have been uploaded to PyPI
- Check the release history (e.g. https://pypi.org/project/opentelemetry-api/#history) on PyPI

If for some reason the action failed, see [Publish failed](#publish-failed) below

## Move stable tag

This will ensure the docs are pointing at the stable release.

```bash
git tag -d stable
git tag stable
git push --delete origin tagname
git push origin stable
```

To validate this worked, ensure the stable build has run successfully: https://readthedocs.org/projects/opentelemetry-python/builds/. If the build has not run automatically, it can be manually trigger via the readthedocs interface.

## Update main

Ensure the version and changelog updates have been applied to main. Update the versions in eachdist.ini once again this time to include the `.dev0` tag and
run eachdist once again:
```bash
./scripts/eachdist.py update_versions --versions stable,prerelease
```

## Hotfix procedure

A `hotfix` is defined as a small change developed to correct a bug that should be released as quickly as possible. Due to the nature of hotfixes, they usually will only affect one or a few packages. Therefore, it usually is not necessary to go through the entire release process outlined above for hotfixes. Follow the below steps how to release a hotfix:

1. Identify the packages that are affected by the bug. Make the changes to those packages, merging to `main`, as quickly as possible.
2. On your local machine, remove the `dev0` tags from the version number and increment the patch version number.
3. On your local machine, update `CHANGELOG.md` with the date of the hotfix change.
4. With administrator privileges for PyPi, manually publish the affected packages.
    1. Install [twine](https://pypi.org/project/twine/) and [build](https://pypi.org/project/build/)
    2. Navigate to where the `pyproject.toml` file exists for the package you want to publish.
    3. To build the package: run `python -m build`.
    4. Validate your built distributions by running `twine check dist/*`.
    5. Upload distributions to PyPi by running `twine upload dist/*`.
5. Note that since hotfixes are manually published, the build scripts for publish after creating a release are not run.

## Troubleshooting

### Publish failed

If for some reason the action failed, do it manually:

- Switch to the release branch (important so we don't publish packages with "dev" versions)
- Build distributions with `./scripts/build.sh`
- Delete distributions we don't want to push (e.g. `testutil`)
- Push to PyPI as `twine upload --skip-existing --verbose dist/*`
- Double check PyPI!
