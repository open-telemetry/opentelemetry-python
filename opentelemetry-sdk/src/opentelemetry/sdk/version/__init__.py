# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""The version of the ``opentelemetry-sdk`` distribution.

``__version__`` is the single place the number is written. Hatch reads it from
here at build time, as declared at ``opentelemetry-sdk/pyproject.toml:87``,
and ``Resource.create`` reports it as the ``telemetry.sdk.version`` attribute
of every default resource.
"""

__version__ = "1.46.0.dev"
