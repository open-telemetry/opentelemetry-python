#!/usr/bin/env python3

from sys import exit, argv
from os import execl
import os
from os.path import dirname, join
from distutils.spawn import find_executable


def run():
    os.environ['PYTHONPATH'] = join(dirname(__file__), 'initialize')
    print(os.environ['PYTHONPATH'])

    python3 = find_executable(argv[1])
    execl(python3, python3, *argv[2:])
    exit(0)


if __name__ == "__main__":
    run()
