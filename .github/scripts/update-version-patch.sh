#!/bin/bash -e

sed -i "/\[stable\]/{n;s/version=.*/version=$1/}" eachdist.ini
sed -i "/\[prerelease\]/{n;s/version=.*/version=$2/}" eachdist.ini

./scripts/eachdist.py update_patch_versions \
    --stable_version=$1 \
    --unstable_version=$2 \
    --stable_version_prev=$3 \
    --unstable_version_prev=$4

