# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import importlib.util
from pathlib import Path
from textwrap import dedent


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
