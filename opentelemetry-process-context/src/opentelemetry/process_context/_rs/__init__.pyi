# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from collections.abc import Mapping
from typing import Any

from opentelemetry.sdk.resources import Resource

def publish_context(
    resource: Resource, attributes: Mapping[str, Any] | None = None
) -> None:
    """Publish or update the process context for the given resource.

    Encodes ``resource`` as a protobuf ``ProcessContext`` message and writes it
    to a named memory mapping (``OTEL_CTX``) that out-of-process readers such
    as the OpenTelemetry eBPF Profiler can discover via ``/proc/<pid>/maps``.

    On the first call the mapping is created and the full header is written. On
    subsequent calls the existing mapping is updated in place using the spec's
    update protocol, so no new mapping is allocated and the header pointer
    remains stable across updates.

    :param resource: The SDK resource whose attributes are to be published.
    :param attributes: Optional supplementary attributes to share with external
        readers.
    :raises OSError: If the memory mapping or clock could not be initialized.
    """

def unpublish_context() -> None:
    """Remove the published process context.

    Zeros the publish timestamp and unmaps the ``OTEL_CTX`` memory region.
    After this call returns, :func:`publish_context` may be called again.

    :raises RuntimeError: If no context has been published yet.
    :raises OSError: If unmapping the memory region failed.
    """
