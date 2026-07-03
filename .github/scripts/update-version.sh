#!/bin/bash -e

sed -i "/\[stable\]/{n;s/version=.*/version=$1/}" repo.ini
sed -i "/\[prerelease\]/{n;s/version=.*/version=$2/}" repo.ini

./scripts/update_version.py --versions stable,prerelease
