from pathlib import Path

from generate_workflows_lib import (
    generate_test_workflow,
    generate_lint_workflow,
    generate_contrib_workflow,
    generate_misc_workflow
)

tox_ini_path = Path(__file__).parent.parent.parent.joinpath("tox.ini")
workflows_directory_path = Path(__file__).parent

generate_test_workflow(
    tox_ini_path,
    workflows_directory_path,
    "ubuntu-latest",
    "windows-latest",
)
generate_lint_workflow(tox_ini_path, workflows_directory_path)
generate_contrib_workflow(workflows_directory_path)
generate_misc_workflow(tox_ini_path, workflows_directory_path)
