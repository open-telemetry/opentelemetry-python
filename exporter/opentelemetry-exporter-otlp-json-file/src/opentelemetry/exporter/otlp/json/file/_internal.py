# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import json


def _format_line(entry: dict) -> str:
    return json.dumps(entry, separators=(",", ".")) + "\n"
