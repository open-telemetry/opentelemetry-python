#!/bin/bash -e

sed -i "/\[stable\]/{n;s/version=.*/version=$1/}" eachdist.ini
sed -i "/\[prerelease\]/{n;s/version=.*/version=$2/}" eachdist.ini

./scripts/eachdist.py update_patch_versions --versions $1,$2,$3,$4
