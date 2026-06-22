# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry.sdk.resources import Resource

def publish_context(resource: Resource) -> None:
    """Publish the process context for the given resource.

    Encodes ``resource`` as a protobuf ``ProcessContext`` message and writes it
    to a named memory mapping (``OTEL_CTX``) that out of process readers such
    as the OpenTelemetry eBPF Profiler can discover via ``/proc/<pid>/maps``.

    The context is a per-process singleton. Calling this function a second time
    without an intervening :func:`unpublish_context` raises :exc:`RuntimeError`.

    :param resource: The SDK resource whose attributes are to be published.
    :raises RuntimeError: If a context has already been published.
    :raises OSError: If the memory mapping or clock could not be initialized.
    """

def update_context(resource: Resource) -> None:
    """Update the published process context with a new resource.

    :func:`publish_context` must be called before this function.

    :param resource: The updated SDK resource to publish.
    :raises RuntimeError: If no context has been published yet.
    :raises OSError: If the clock could not be read.
    """

def unpublish_context() -> None:
    """Remove the published process context.

    Zeros the publish timestamp and unmaps the ``OTEL_CTX`` memory region.
    After this call returns, :func:`publish_context` may be called again.

    :raises RuntimeError: If no context has been published yet.
    :raises OSError: If unmapping the memory region failed.
    """
