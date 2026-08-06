# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access,bare-except

import os
import sys

from opentelemetry.process_context import publish_context, unpublish_context
from opentelemetry.sdk.resources import Resource

resource = Resource({"service.name": "test", "version": 1})
publish_context(resource)

pid = os.fork()
if not pid:
    # Child inherits the parent's region (stale owner PID). It never published,
    # so unpublish must raise RuntimeError (NotPublished) rather than crash.
    try:
        unpublish_context()
    except RuntimeError:
        os._exit(0)
    except:  # noqa: E722
        os._exit(2)
    # No exception at all is also wrong: the child published nothing.
    os._exit(1)

_, status = os.waitpid(pid, 0)
if not (os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0):
    sys.exit(1)

# The parent's own mapping is untouched and still usable.
try:
    unpublish_context()
except:  # noqa: E722
    sys.exit(1)
sys.exit(0)
