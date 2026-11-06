#!/bin/sh

# This script builds wheels for the API, SDK, and extension packages in the
# dist/ dir, to be uploaded to PyPI.

set -ev

# Exclude packages uploaded within the last 3 days across all uv invocations,
# ensuring build backend dependencies (e.g. hatchling) also inherit the cutoff.
export UV_EXCLUDE_NEWER=3d

BASEDIR=$(dirname "$(readlink -f "$(dirname "$0")")")
DISTDIR=dist

(
  cd "$BASEDIR"

  # Ensure no untracked or modified files exist in the checkout before building
  if [ -n "$(git status --porcelain)" ]; then
    echo "Error! Working tree is dirty before build:"
    git status --porcelain
    exit 1
  fi

  mkdir -p "$DISTDIR"
  rm -rf "${DISTDIR:?}/"*

  for d in opentelemetry-api/ opentelemetry-configuration/ opentelemetry-sdk/ opentelemetry-proto/ opentelemetry-proto-json/ opentelemetry-semantic-conventions/ exporter/*/ shim/*/ propagator/*/ tests/opentelemetry-test-utils/; do
    (
      echo "building $d"
      cd "$d"
      # Some ext directories (such as docker tests) are not intended to be
      # packaged. Verify the intent by looking for a pyproject.toml.
      if [ -f pyproject.toml ]; then
        uv build --out-dir "$BASEDIR/$DISTDIR/"
      fi
    )
  done

  # Audit built wheel contents against startup-hook (.pth / sitecustomize.py)
  # and *.data/ injection attacks (e.g., LiteLLM v1.107.0 supply-chain vector).
  python3 - "$BASEDIR/$DISTDIR" <<'PYEOF'
import pathlib
import sys
import zipfile

distdir = pathlib.Path(sys.argv[1])
wheels = sorted(distdir.glob("*.whl"))
if not wheels:
    sys.exit(f"Error! No wheels found in {distdir}")

for wheel in wheels:
    dist_and_version = "-".join(wheel.name.split("-")[:2])
    expected_dist_info = f"{dist_and_version}.dist-info/"
    with zipfile.ZipFile(wheel) as zf:
        for name in zf.namelist():
            basename = pathlib.PurePosixPath(name).name
            if name.endswith(".pth") or basename in {"sitecustomize.py", "usercustomize.py"}:
                sys.exit(f"Error! Forbidden startup hook file in {wheel.name}: {name}")
            if not (name.startswith("opentelemetry/") or name.startswith(expected_dist_info)):
                sys.exit(
                    f"Error! Unexpected top-level path in {wheel.name}: {name} "
                    f"(expected 'opentelemetry/' or '{expected_dist_info}')"
                )
    print(f"Verified wheel contents for {wheel.name} ({len(zf.namelist())} files).")
PYEOF
)
