#!/usr/bin/env bash
#
# Usage: 
#   ./scripts/runtox.sh py312 <pytest-args>
#
# Runs all environments with substring "py312" and the given arguments for pytest
# 

# Print commands and exit on first error
set -ex

# Find the right tox executable
if [ -n "$TOXPATH" ]; then
    true
elif which tox &> /dev/null; then
    TOXPATH=tox
else
    TOXPATH=./.venv/bin/tox
fi

# Find the environments matching the searchstring
searchstring="$1"
ENV="$($TOXPATH -l | grep -- "$searchstring" | tr $'\n' ',')"

if [ -z "${ENV}" ]; then
    echo "No targets found. Skipping."
    exit 0
fi

# Run tox with all matching environments
exec $TOXPATH -e "$ENV" -- "${@:2}"
