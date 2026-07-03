#!/usr/bin/env python3
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from argparse import ArgumentParser
from sys import exit

from repo_targets import find_projectroot
from toml import load


def parse_args():
    parser = ArgumentParser(description="Get the version for a release")
    parser.add_argument("--mode", "-m", default="DEFAULT")
    return parser.parse_args()


def main():
    args = parse_args()
    cfg = load(find_projectroot() / "repo.toml")
    print(cfg[args.mode]["version"])


if __name__ == "__main__":
    exit(main())
