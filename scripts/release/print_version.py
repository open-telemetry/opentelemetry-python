#!/usr/bin/env python3
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Prints repo.toml's current stable or prerelease version to stdout,
for the release workflows to capture (e.g.
`$(./scripts/release/print_version.py --stable)`)."""

from argparse import ArgumentParser
from pathlib import Path
from sys import path

path.insert(0, str(Path(__file__).resolve().parent.parent))

from repo_targets import find_projectroot
from tomlkit import load

parser = ArgumentParser(description="Get the version for a release")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument(
    "--stable", dest="section", action="store_const", const="stable"
)
group.add_argument(
    "--unstable", dest="section", action="store_const", const="prerelease"
)

with open(find_projectroot() / "repo.toml", encoding="utf-8") as file:
    print(load(file)[parser.parse_args().section]["version"])
