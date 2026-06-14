# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""
The OpenTelemetry OpenCensus shim is a library which allows an easy migration from OpenCensus
to OpenTelemetry. Additional details can be found `in the specification
<https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/compatibility/opencensus.md>`_.

The shim consists of a set of classes which implement the OpenCensus Python API while using
OpenTelemetry constructs behind the scenes. Its purpose is to allow applications which are
already instrumented using OpenCensus to start using OpenTelemetry with minimal effort, without
having to rewrite large portions of the codebase.
"""

from opentelemetry.shim.opencensus._patch import install_shim, uninstall_shim

__all__ = [
    "install_shim",
    "uninstall_shim",
]

# TODO: Decide when this should be called.
# 1. defensive import in opentelemetry-api
# 2. defensive import directly in OpenCensus, although that would require a release
# 3. ask the user to do it
# install_shim()
