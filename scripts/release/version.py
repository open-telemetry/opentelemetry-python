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
parser.add_argument("--mode", "-m", default="DEFAULT")
args = parser.parse_args()

with open(find_projectroot() / "repo.toml", encoding="utf-8") as file:
    cfg = load(file)
print(cfg[args.mode]["version"])
