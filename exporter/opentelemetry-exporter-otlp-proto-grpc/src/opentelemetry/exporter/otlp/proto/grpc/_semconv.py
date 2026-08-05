# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Local copies of unstable/incubating semantic-convention attributes

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Final

_RPC_RESPONSE_STATUS_CODE: Final[str] = "rpc.response.status_code"
