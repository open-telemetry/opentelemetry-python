# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import importlib.util
from configparser import ConfigParser
from pathlib import Path
from textwrap import dedent

from toml import load

PACKAGE_ROOT_GLOBS = (
    "opentelemetry-*/pyproject.toml",
    "exporter/opentelemetry-*/pyproject.toml",
    "propagator/opentelemetry-*/pyproject.toml",
    "shim/opentelemetry-*/pyproject.toml",
    "tests/opentelemetry-*/pyproject.toml",
    "codegen/opentelemetry-*/pyproject.toml",
)
PRIVATE_PACKAGE_CLASSIFIER = "Private :: Do Not Upload"


def load_eachdist():
    script = Path(__file__).parents[1] / "eachdist.py"
    spec = importlib.util.spec_from_file_location("eachdist", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_pyproject(target, dependencies):
    target.mkdir()
    target.joinpath("pyproject.toml").write_text(
        dedent(
            f"""
            [project]
            dependencies = [
              {dependencies}
            ]
            """
        ),
        encoding="utf-8",
    )


def write_versioned_project(target, name, version):
    version_file = target / "src" / "opentelemetry" / "version" / "__init__.py"
    version_file.parent.mkdir(parents=True)
    version_file.write_text(
        f'__version__ = "{version}"\n',
        encoding="utf-8",
    )
    target.mkdir(exist_ok=True)
    target.joinpath("pyproject.toml").write_text(
        dedent(
            f"""
            [project]
            name = "{name}"

            [tool.hatch.version]
            path = "src/opentelemetry/version/__init__.py"
            """
        ),
        encoding="utf-8",
    )


def project_root():
    return Path(__file__).parents[2]


def package_name(pyproject):
    project = load(pyproject)["project"]
    if PRIVATE_PACKAGE_CLASSIFIER in project.get("classifiers", ()):
        return None
    return project["name"]


def test_all_release_packages_are_listed_in_eachdist():
    root = project_root()
    releasable_package_names = {
        name
        for package_glob in PACKAGE_ROOT_GLOBS
        for pyproject in root.glob(package_glob)
        if (name := package_name(pyproject)) is not None
    }

    config = ConfigParser()
    config.read(root / "eachdist.ini")
    eachdist_package_names = set(config["stable"]["packages"].split()) | set(
        config["prerelease"]["packages"].split()
    )

    missing_package_names = sorted(
        releasable_package_names - eachdist_package_names
    )
    assert not missing_package_names, (
        "packages missing from eachdist.ini: "
        f"{', '.join(missing_package_names)}"
    )


def test_update_dependencies_matches_exact_package_name(tmp_path):
    eachdist = load_eachdist()
    target = tmp_path / "target"
    write_pyproject(
        target,
        '"opentelemetry-proto == 1.44.0.dev",\n'
        '  "opentelemetry-proto-json == 0.65b0.dev",',
    )

    eachdist.update_dependencies(
        [target],
        "1.44.0",
        ["opentelemetry-proto"],
    )

    pyproject = target.joinpath("pyproject.toml").read_text(encoding="utf-8")
    assert '"opentelemetry-proto == 1.44.0",' in pyproject
    assert '"opentelemetry-proto-json == 0.65b0.dev",' in pyproject


def test_update_patch_dependencies_matches_exact_package_name(tmp_path):
    eachdist = load_eachdist()
    target = tmp_path / "target"
    write_pyproject(
        target,
        '"opentelemetry-proto == 1.43.0",\n'
        '  "opentelemetry-proto-json == 1.43.0",',
    )

    eachdist.update_patch_dependencies(
        [target],
        "1.43.1",
        "1.43.0",
        ["opentelemetry-proto"],
    )

    pyproject = target.joinpath("pyproject.toml").read_text(encoding="utf-8")
    assert '"opentelemetry-proto == 1.43.1",' in pyproject
    assert '"opentelemetry-proto-json == 1.43.0",' in pyproject


def test_update_version_files_matches_exact_project_name(tmp_path):
    eachdist = load_eachdist()
    proto = tmp_path / "opentelemetry-proto"
    proto_json = tmp_path / "opentelemetry-proto-json"
    write_versioned_project(
        proto,
        "opentelemetry-proto",
        "1.44.0.dev",
    )
    write_versioned_project(
        proto_json,
        "opentelemetry-proto-json",
        "0.65b0.dev",
    )

    eachdist.update_version_files(
        [proto, proto_json],
        "1.45.0.dev",
        ["opentelemetry-proto"],
    )

    assert (
        proto.joinpath("src/opentelemetry/version/__init__.py").read_text(
            encoding="utf-8"
        )
        == '__version__ = "1.45.0.dev"\n'
    )
    assert (
        proto_json.joinpath("src/opentelemetry/version/__init__.py").read_text(
            encoding="utf-8"
        )
        == '__version__ = "0.65b0.dev"\n'
    )
