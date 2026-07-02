#!/bin/bash -e

sed -i "/\[stable\]/{n;s/version=.*/version=$1/}" repo.ini
sed -i "/\[prerelease\]/{n;s/version=.*/version=$2/}" repo.ini

./scripts/release.py update_versions --versions stable,prerelease
