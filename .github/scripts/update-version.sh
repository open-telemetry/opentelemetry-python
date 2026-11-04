#!/bin/bash -e

sed -i "/\[stable\]/{n;s/version=.*/version=$1/}" eachdist.ini
sed -i "/\[prerelease\]/{n;s/version=.*/version=$2/}" eachdist.ini

uv run --no-project --exclude-newer 3d --with toml ./scripts/eachdist.py update_versions --versions stable,prerelease
