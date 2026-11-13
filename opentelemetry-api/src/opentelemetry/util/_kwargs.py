# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from typing import Any


def _non_default_kwargs(**kwargs: Any) -> dict[str, Any]:
    """Returns the keyword arguments whose value is not the ``None`` default.

    Proxies use this to forward optional keyword arguments only when they were
    set, so the delegate sees the same call an older API would make.
    """
    return {key: value for key, value in kwargs.items() if value is not None}
