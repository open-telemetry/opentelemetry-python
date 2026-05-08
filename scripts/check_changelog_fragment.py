# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Check for changelog fragments on feature branches.

Used as a pre-commit hook via .pre-commit-config.yaml (runs with tox -e precommit).
"""

import subprocess
import sys


def main():
    # Find the merge base with origin/main
    try:
        merge_base = subprocess.run(
            ["git", "merge-base", "origin/main", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        # Can't determine merge base (e.g. shallow clone, no remote)
        return 0

    # Check if we're on main itself
    try:
        current_ref = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        return 0

    if merge_base == current_ref:
        # On main or no divergence, skip check
        return 0

    # Check if any changelog fragments have been added
    try:
        diff_output = subprocess.run(
            [
                "git",
                "diff",
                "--diff-filter=A",
                "--name-only",
                merge_base,
                "--",
                ".changelog/",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        return 0

    if diff_output:
        # Fragment(s) found
        return 0

    print("⚠ No changelog fragment found on this branch.")
    print()
    print("Create one with:")
    print('  tox -e new-changelog -- PR_NUMBER TYPE "Description"')
    print("  where TYPE is one of: added, changed, deprecated, removed, fixed")
    print()
    print("Or skip this check with: SKIP=changelog tox -e precommit")
    return 1


if __name__ == "__main__":
    sys.exit(main())
