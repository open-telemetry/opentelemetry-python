#!/bin/bash -e

sed -i "/\[stable\]/{n;s/version=.*/version=$1/}" repo.ini
sed -i "/\[prerelease\]/{n;s/version=.*/version=$2/}" repo.ini

./scripts/update_patch_version.py \
    --stable_version=$1 \
    --unstable_version=$2 \
    --stable_version_prev=$3 \
    --unstable_version_prev=$4

