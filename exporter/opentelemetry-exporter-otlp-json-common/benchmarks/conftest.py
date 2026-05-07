# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import sys
from pathlib import Path

_pkg_root = str(Path(__file__).resolve().parent.parent)


def pytest_configure(config):
    """Add the package root to sys.path so 'from tests import ...' works."""
    if _pkg_root not in sys.path:
        sys.path.insert(0, _pkg_root)
