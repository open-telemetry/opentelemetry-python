#!/usr/bin/env python3

import argparse
import shlex
import shutil
import subprocess
import sys
from collections import namedtuple
from configparser import ConfigParser
from itertools import chain
from pathlib import Path, PurePath

DEFAULT_ALLSEP = " "
DEFAULT_ALLFMT = "{rel}"

try:
    subprocess_run = subprocess.run
except AttributeError:  # Py < 3.5 compat
    CompletedProcess = namedtuple("CompletedProcess", "returncode")

    def subprocess_run(*args, **kwargs):
        check = kwargs.pop("check", False)
        if check:
            subprocess.check_call(*args, **kwargs)
            return CompletedProcess(returncode=0)
        else:
            return CompletedProcess(
                returncode=subprocess.call(*args, **kwargs)
            )


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Do something for each or all distributions in the repository."
    )
    parser.set_defaults(parser=parser)
    parser.add_argument("--dry-run", action="store_true")
    subparsers = parser.add_subparsers()

    excparser = subparsers.add_parser(
        "exec", help="Run an executable for each or all distributions."
    )
    excparser.set_defaults(func=execute_args)
    excparser.add_argument("format")
    excparser.add_argument("--all", nargs="?", const=DEFAULT_ALLFMT)
    excparser.add_argument("--allsep")
    excparser.add_argument(
        "--allowexitcode", type=int, action="append", default=[0]
    )
    excparser.add_argument(
        "--mode",
        "-m",
        default="DEFAULT",
        help="Section of config file to use for target selection configuration.",
    )

    instparser = subparsers.add_parser(
        "install", help="Install all distributions."
    )

    def setup_instparser(instparser):
        instparser.set_defaults(func=install_args)
        instparser.add_argument("pipargs", nargs=argparse.REMAINDER)

    setup_instparser(instparser)
    instparser.add_argument("--editable", "-e", action="store_true")
    instparser.add_argument("--with-dev-deps", action="store_true")

    devparser = subparsers.add_parser(
        "develop",
        help="Install all distributions editable + dev dependencies.",
    )
    setup_instparser(devparser)
    devparser.set_defaults(editable=True, with_dev_deps=True)

    lintparser = subparsers.add_parser(
        "lint", help="Lint everything, autofixing if possible."
    )
    lintparser.add_argument("--check-only", action="store_true")
    lintparser.set_defaults(func=lint_args)

    testparser = subparsers.add_parser(
        "test",
        help="Test everything (run pytest yourself for more complex operations).",
    )
    testparser.set_defaults(func=test_args)
    testparser.add_argument("pytestargs", nargs=argparse.REMAINDER)

    return parser.parse_args(args)


def find_projectroot(search_start=Path(".")):
    root = search_start.resolve()
    for root in chain((root,), root.parents):
        if any((root / marker).exists() for marker in (".git", "tox.ini")):
            return root
    return None


def find_targets_unordered(rootpath):
    for subdir in rootpath.iterdir():
        if not subdir.is_dir():
            continue
        if subdir.name.startswith(".") or subdir.name.startswith("venv"):
            continue
        if any(
            (subdir / marker).exists()
            for marker in ("setup.py", "pyproject.toml")
        ):
            yield subdir
        else:
            yield from find_targets_unordered(subdir)


def getlistcfg(strval):
    return [
        val.strip()
        for line in strval.split("\n")
        for val in line.split(",")
        if val.strip()
    ]


def find_targets(mode, rootpath):
    if not rootpath:
        sys.exit("Could not find a root directory.")

    cfg = ConfigParser()
    cfg.read(str(rootpath / "eachdist.ini"))
    mcfg = cfg[mode]

    targets = list(find_targets_unordered(rootpath))
    if "sortfirst" in mcfg:
        sortfirst = getlistcfg(mcfg["sortfirst"])

        def keyfunc(path):
            path = path.relative_to(rootpath)
            for i, pattern in enumerate(sortfirst):
                if path.match(pattern):
                    return i
            return float("inf")

        targets.sort(key=keyfunc)

    subglobs = getlistcfg(mcfg.get("subglob", ""))
    if subglobs:
        targets = [
            newentry
            for newentry in (
                target / subdir
                for target in targets
                for subglob in subglobs
                # We need to special-case the dot, because glob fails to parse that with an IndexError.
                for subdir in (
                    (target,) if subglob == "." else target.glob(subglob)
                )
            )
            if ".egg-info" not in str(newentry) and newentry.exists()
        ]

    return targets


def runsubprocess(dry_run, params, *args, **kwargs):
    cmdstr = join_args(params)
    if dry_run:
        print(cmdstr)
        return None

    # Py < 3.6 compat.
    cwd = kwargs.get("cwd")
    if cwd and isinstance(cwd, PurePath):
        kwargs["cwd"] = str(cwd)

    print(">>>", cmdstr, file=sys.stderr)

    # This is a workaround for subprocess.run(['python']) leaving the virtualenv on Win32.
    # The cause for this is that when running the python.exe in a virtualenv,
    # the wrapper executable launches the global python as a subprocess and the search sequence
    # for CreateProcessW which subprocess.run and Popen use is a follows
    # (https://docs.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw):
    # > 1. The directory from which the application loaded.
    # This will be the directory of the global python.exe, not the venv directory, due to the suprocess mechanism.
    # > 6. The directories that are listed in the PATH environment variable.
    # Only this would find the "correct" python.exe.

    params = list(params)
    executable = shutil.which(params[0])  # On Win32, pytho
    if executable:
        params[0] = executable
    try:
        return subprocess_run(params, *args, **kwargs)
    except OSError as exc:
        raise ValueError(
            "Failed executing " + repr(params) + ": " + str(exc)
        ) from exc


def execute_args(args):
    if args.allsep and not args.all:
        args.parser.error("--allsep specified but not --all.")

    if args.all and not args.allsep:
        args.allsep = DEFAULT_ALLSEP

    rootpath = find_projectroot()
    targets = find_targets(args.mode, rootpath)
    if not targets:
        sys.exit("Error: No targets selected (root: {})".format(rootpath))

    def fmt_for_path(fmt, path):
        return fmt.format(
            path.as_posix(),
            rel=path.relative_to(rootpath).as_posix(),
            raw=path,
            rawrel=path.relative_to(rootpath),
        )

    def _runcmd(cmd):
        result = runsubprocess(
            args.dry_run, shlex.split(cmd), cwd=rootpath, check=False
        )
        if result is not None and result.returncode not in args.allowexitcode:
            print(
                "'{}' failed with code {}".format(cmd, result.returncode),
                file=sys.stderr,
            )
            sys.exit(result.returncode)

    if args.all:
        allstr = args.allsep.join(
            fmt_for_path(args.all, path) for path in targets
        )
        cmd = args.format.format(allstr)
        _runcmd(cmd)
    else:
        for target in targets:
            cmd = fmt_for_path(args.format, target)
            _runcmd(cmd)


def clean_remainder_args(remainder_args):
    if remainder_args and remainder_args[0] == "--":
        del remainder_args[0]


def join_args(arglist):
    return " ".join(map(shlex.quote, arglist))


def install_args(args):
    clean_remainder_args(args.pipargs)

    if args.with_dev_deps:
        runsubprocess(
            args.dry_run,
            [
                "python",
                "-m",
                "pip",
                "install",
                "--upgrade",
                "pip",
                "setuptools",
                "wheel",
            ]
            + args.pipargs,
            check=True,
        )

    allfmt = "-e 'file://{}'" if args.editable else "'file://{}'"
    execute_args(
        parse_subargs(
            args,
            (
                "exec",
                "python -m pip install {} " + join_args(args.pipargs),
                "--all",
                allfmt,
            ),
        )
    )
    if args.with_dev_deps:
        rootpath = find_projectroot()
        runsubprocess(
            args.dry_run,
            [
                "python",
                "-m",
                "pip",
                "install",
                "--upgrade",
                "-r",
                str(rootpath / "dev-requirements.txt"),
            ]
            + args.pipargs,
            check=True,
        )


def parse_subargs(parentargs, args):
    subargs = parse_args(args)
    subargs.dry_run = parentargs.dry_run or subargs.dry_run
    return subargs


def lint_args(args):
    rootdir = str(find_projectroot())

    runsubprocess(
        args.dry_run,
        ("black", rootdir)
        + (("--diff", "--check") if args.check_only else ()),
        check=True,
    )
    runsubprocess(
        args.dry_run,
        ("isort", "--recursive", rootdir)
        + (("--diff", "--check-only") if args.check_only else ()),
        check=True,
    )
    runsubprocess(args.dry_run, ("flake8", rootdir), check=True)
    execute_args(
        parse_subargs(
            args, ("exec", "pylint {}", "--all", "--mode", "lintroots",),
        )
    )


def test_args(args):
    clean_remainder_args(args.pytestargs)
    execute_args(
        parse_subargs(
            args,
            (
                "exec",
                "pytest {} " + join_args(args.pytestargs),
                "--mode",
                "testroots",
            ),
        )
    )


def main():
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
