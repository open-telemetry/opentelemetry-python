import argparse
import sys

import griffe
from eachdist import find_projectroot, find_targets


def get_modules() -> list[str]:
    rootpath = find_projectroot()
    targets = find_targets("DEFAULT", rootpath)

    dirs_to_exclude = [
        "docs",
        "scripts",
        "opentelemetry-docker-tests",
        "examples",
        "_template",
    ]

    packages = []
    for target in targets:
        rel_path = target.relative_to(rootpath)
        if not any(excluded in str(rel_path) for excluded in dirs_to_exclude):
            packages.append(str(rel_path / "src"))
    return packages


def main():
    parser = argparse.ArgumentParser(
        description="Check for breaking changes using griffe",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--module",
        default="opentelemetry",
        help="Name of the module to check for breaking changes (e.g., opentelemetry, opentelemetry.sdk, opentelemetry.sdk.resources)",
    )
    parser.add_argument(
        "--against",
        default="main",
        help="Git ref to compare against (e.g., branch, tag, or commit)",
    )
    args = parser.parse_args()

    modules = get_modules()
    base = griffe.load(args.module, search_paths=modules)
    against = griffe.load_git(
        args.module, ref=args.against, search_paths=modules
    )

    breakages = list(griffe.find_breaking_changes(against, base))

    if breakages:
        for b in breakages:
            # We can use `b.explain()` to get a detailed explanation of the breaking change
            # and we can iterate over breakages to perform more complex logic
            # like skipping per object.path or breakage type
            print(b.explain())
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
