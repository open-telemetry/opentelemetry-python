from collections import defaultdict
from pathlib import Path
from re import compile as re_compile

from jinja2 import Environment, FileSystemLoader
from tox.config.cli.parse import get_options
from tox.config.sets import CoreConfigSet
from tox.config.source.tox_ini import ToxIni
from tox.session.state import State

_tox_test_env_regex = re_compile(
    r"(?P<python_version>py\w+)-test-"
    r"(?P<name>[-\w]+\w)-?(?P<test_requirements>\d+)?"
)
_tox_lint_env_regex = re_compile(r"lint-(?P<name>[-\w]+)")
_tox_contrib_env_regex = re_compile(
    r"py39-test-(?P<name>[-\w]+\w)-?(?P<contrib_requirements>\d+)?"
)


def get_tox_envs(tox_ini_path: Path) -> list:
    tox_ini = ToxIni(tox_ini_path)

    conf = State(get_options(), []).conf

    tox_section = next(tox_ini.sections())

    core_config_set = CoreConfigSet(
        conf, tox_section, tox_ini_path.parent, tox_ini_path
    )

    (
        core_config_set.loaders.extend(
            tox_ini.get_loaders(
                tox_section,
                base=[],
                override_map=defaultdict(list, {}),
                conf=core_config_set,
            )
        )
    )

    return core_config_set.load("env_list")


def get_test_job_datas(tox_envs: list, operating_systems: list) -> list:
    os_alias = {"ubuntu-latest": "Ubuntu", "windows-latest": "Windows"}

    python_version_alias = {
        "pypy3": "pypy-3.9",
        "py39": "3.9",
        "py310": "3.10",
        "py311": "3.11",
        "py312": "3.12",
        "py313": "3.13",
    }

    test_job_datas = []

    for operating_system in operating_systems:
        for tox_env in tox_envs:
            tox_test_env_match = _tox_test_env_regex.match(tox_env)

            if tox_test_env_match is None:
                continue

            groups = tox_test_env_match.groupdict()

            aliased_python_version = python_version_alias[
                groups["python_version"]
            ]
            tox_env = tox_test_env_match.string

            test_requirements = groups["test_requirements"]

            if test_requirements is None:
                test_requirements = " "

            else:
                test_requirements = f"-{test_requirements} "

            test_job_datas.append(
                {
                    "name": f"{tox_env}_{operating_system}",
                    "ui_name": (
                        f"{groups['name']}"
                        f"{test_requirements}"
                        f"{aliased_python_version} "
                        f"{os_alias[operating_system]}"
                    ),
                    "python_version": aliased_python_version,
                    "tox_env": tox_env,
                    "os": operating_system,
                }
            )

    return test_job_datas


def get_lint_job_datas(tox_envs: list) -> list:
    lint_job_datas = []

    for tox_env in tox_envs:
        tox_lint_env_match = _tox_lint_env_regex.match(tox_env)

        if tox_lint_env_match is None:
            continue

        tox_env = tox_lint_env_match.string

        lint_job_datas.append(
            {
                "name": f"{tox_env}",
                "ui_name": f"{tox_lint_env_match.groupdict()['name']}",
                "tox_env": tox_env,
            }
        )

    return lint_job_datas


def get_misc_job_datas(tox_envs: list) -> list:
    regex_patterns = [
        _tox_test_env_regex,
        _tox_lint_env_regex,
        _tox_contrib_env_regex,
        re_compile(r"benchmark.+"),
    ]

    return [
        tox_env
        for tox_env in tox_envs
        if not any(pattern.match(tox_env) for pattern in regex_patterns)
    ]


def _generate_workflow(
    job_datas: list,
    template_name: str,
    output_dir: Path,
    max_jobs: int = 250,
):
    # Github seems to limit the amount of jobs in a workflow file, that is why
    # they are split in groups of 250 per workflow file.
    for file_number, job_datas in enumerate(
        [
            job_datas[index : index + max_jobs]
            for index in range(0, len(job_datas), max_jobs)
        ]
    ):
        with open(
            output_dir.joinpath(f"{template_name}_{file_number}.yml"), "w"
        ) as test_yml_file:
            test_yml_file.write(
                Environment(
                    loader=FileSystemLoader(
                        Path(__file__).parent.joinpath("templates")
                    )
                )
                .get_template(f"{template_name}.yml.j2")
                .render(job_datas=job_datas, file_number=file_number)
            )
            test_yml_file.write("\n")


def generate_test_workflow(
    tox_ini_path: Path, workflow_directory_path: Path, operating_systems
) -> None:
    _generate_workflow(
        get_test_job_datas(get_tox_envs(tox_ini_path), operating_systems),
        "test",
        workflow_directory_path,
    )


def generate_lint_workflow(
    tox_ini_path: Path,
    workflow_directory_path: Path,
) -> None:
    _generate_workflow(
        get_lint_job_datas(get_tox_envs(tox_ini_path)),
        "lint",
        workflow_directory_path,
    )


def generate_misc_workflow(
    tox_ini_path: Path,
    workflow_directory_path: Path,
) -> None:
    _generate_workflow(
        get_misc_job_datas(get_tox_envs(tox_ini_path)),
        "misc",
        workflow_directory_path,
    )


if __name__ == "__main__":
    tox_ini_path = Path(__file__).parent.parent.parent.joinpath("tox.ini")
    output_dir = Path(__file__).parent
    generate_test_workflow(
        tox_ini_path, output_dir, ["ubuntu-latest", "windows-latest"]
    )
    generate_lint_workflow(tox_ini_path, output_dir)
    generate_misc_workflow(tox_ini_path, output_dir)
