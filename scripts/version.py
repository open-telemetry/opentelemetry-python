#!/usr/bin/env python3
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import argparse
import sys
from configparser import ConfigParser

from repo_targets import find_projectroot


def parse_args():
    parser = argparse.ArgumentParser(
        description="Get the version for a release"
    )
    parser.add_argument("--mode", "-m", default="DEFAULT")
    return parser.parse_args()


def main():
    args = parse_args()
    cfg = ConfigParser()
    cfg.read(str(find_projectroot() / "repo.ini"))
    print(cfg[args.mode]["version"])


if __name__ == "__main__":
    sys.exit(main())
