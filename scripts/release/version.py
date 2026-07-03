#!/usr/bin/env python3
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from argparse import ArgumentParser
from pathlib import Path
from sys import path

path.insert(0, str(Path(__file__).resolve().parent.parent))

from repo_targets import find_projectroot
from tomlkit import load

parser = ArgumentParser(description="Get the version for a release")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--stable", action="store_true")
group.add_argument("--unstable", action="store_true")
args = parser.parse_args()

section = "stable" if args.stable else "prerelease"

with open(find_projectroot() / "repo.toml", encoding="utf-8") as file:
    cfg = load(file)
print(cfg[section]["version"])
