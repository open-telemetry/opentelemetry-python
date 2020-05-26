# Releasing OpenTelemetry Packages (for maintainers only)
This document explains how to publish all OT modules at version x.y.z. Ensure that you’re following semver when choosing a version number.

Release Process:
* [Create a new branch](#create-a-new-branch)
* [Open a Pull Request](#open-a-pull-request)
* [Create a Release](#Create-a-Release)
* [Move stable tag](#Move-stable-tag)
* [Update master](#Update-master)
* [Check PyPI](#Check-PyPI)
* [Troubleshooting](#troubleshooting)


## Create a new branch
The following script does the following:
- update master locally
- creates a new release branch `release/<version>`
- updates version and changelog files
- commits the change to a new branch `release/<version>-auto`

*NOTE: This script was run by a GitHub Action but required the Action bot to be excluded from the CLA check, which it currently is not.*

```bash
./scripts/prepare_release.sh 0.7b0
```

## Open a Pull Request

The PR should be opened from the `release/<version>-auto` branch created as part of running `prepare_release.sh` in the steps above.

## Create a Release

- Create the GH release from the release branch, using a new tag for this micro version, e.g. `v0.7.0`
- Copy the changelogs from all packages that changed into the release notes (and reformat to remove hard line wraps)


## Check PyPI

This should be handled automatically on release by the [publish action](https://github.com/open-telemetry/opentelemetry-python/blob/master/.github/workflows/publish.yml).

 - Check the [action logs](https://github.com/open-telemetry/opentelemetry-python/actions?query=workflow%3APublish) to make sure packages have been uploaded to PyPI
- Check the release history (e.g. https://pypi.org/project/opentelemetry-api/#history) on PyPI

If for some reason the action failed, see [Publish failed](#publish-failed) below

## Move stable tag

This will ensure the docs are pointing at the stable release.

```bash
git tag -d stable
git tag stable
git push origin stable
```

## Update master

Ensure the version and changelog updates have been applied to master.

```bash
# checkout a new branch from master
git checkout -b v0.7b0-master-update
# cherry pick the change from the release branch
git cherry-pick $(git log -n 1 origin/release/0.7b0 --format="%H")
# update the version number, make it a "dev" greater than release number, e.g. 0.8.dev0
perl -i -p -e 's/0.7b0/0.8.dev0/' $(git grep -l "0.7b0" | grep -vi CHANGELOG)
# open a PR targeting master see #331
git commit -m
```

## Troubleshooting

### Publish failed

If for some reason the action failed, do it manually:

- To avoid pushing untracked changes, check out the repo in a new dir
- Switch to the release branch (important so we don't publish packages with "dev" versions)
- Build distributions with `./scripts/build.sh`
- Delete distributions we don't want to push (e.g. `testutil`)
- Push to PyPI as `twine upload --skip-existing --verbose dist/*`
- Double check PyPI!
