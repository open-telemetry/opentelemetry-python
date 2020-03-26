"""Test script to check README.rst files for syntax errors."""
import argparse
import sys
from pathlib import Path

import readme_renderer.rst


def is_valid_rst(path):
    """Checks if RST can be rendered on PyPI."""
    with open(path) as f:
        markup = f.read()
    return readme_renderer.rst.render(markup) is not None


def parse_args():
    parser = argparse.ArgumentParser(
        description="Checks README.rst file in path for syntax errors."
    )
    parser.add_argument(
        "paths", nargs="+", help="paths containing a README.rst to test"
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    error = False
    all_readmes_found = True

    for path in map(Path, args.path):
        readme = path / "README.rst"
        if not readme.exists():
            all_readmes_found = False
            print("✗ No README.rst in", str(path))
            continue
        if not is_valid_rst(readme):
            error = True
            print("✗ RST syntax errors in", readme)
            continue
        if args.verbose:
            print("✓", readme)

    if error:
        sys.exit(1)
    if all_readmes_found:
        print("All clear.")
    else:
        print("No errors found but not all packages have a README.rst")
