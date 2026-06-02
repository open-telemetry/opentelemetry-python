# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Shared post-fork handling of ``service.instance.id`` for SDK providers.

When a prefork server (gunicorn, uWSGI, ...) forks worker processes, every
worker inherits the same :class:`~opentelemetry.sdk.resources.Resource` -
including the same ``service.instance.id`` - from the master process. Exporting
telemetry from several workers under one identity collides in the backend
(last-write-wins instead of correct aggregation).

This module owns a *single* :func:`os.register_at_fork` hook and a registry of
providers. After a fork, **one** fresh ``service.instance.id`` is generated and
applied to *every* registered provider, so all signals (metrics and traces) in
a given worker share the same, unique instance id. Providers created *after* the
fork adopt the same id at construction time via :func:`register_provider`.
"""

from __future__ import annotations

import os
import weakref
from threading import Lock
from typing import Optional, Protocol, runtime_checkable
from uuid import uuid4

from opentelemetry.sdk.resources import SERVICE_INSTANCE_ID, Resource


@runtime_checkable
class _ForkAwareProvider(Protocol):
    def _reset_service_instance_id(self, service_instance_id: str) -> None: ...


_lock = Lock()
# WeakSet so providers that go out of scope are dropped automatically, matching
# the WeakMethod/WeakSet pattern used elsewhere in the SDK for fork hooks.
_providers: "weakref.WeakSet[_ForkAwareProvider]" = weakref.WeakSet()
# The instance id for the current process generation. ``None`` until the first
# fork, so providers in a never-forked process keep the id already present in
# their resource (the one from the default resource detector).
_service_instance_id: Optional[str] = None


def reset_service_instance_id(resource: Resource, service_instance_id: str) -> Resource:
    """Return ``resource`` with ``service.instance.id`` replaced.

    All other resource attributes are preserved via :meth:`Resource.merge`.
    """
    return resource.merge(Resource({SERVICE_INSTANCE_ID: service_instance_id}))


def register_provider(provider: _ForkAwareProvider) -> None:
    """Register ``provider`` so it is refreshed on the next fork.

    If the current process is already a forked child (i.e. a fork happened
    before this provider was created), the provider immediately adopts the
    child's shared instance id so late-created providers stay consistent with
    the ones that existed at fork time.
    """
    with _lock:
        _providers.add(provider)
        service_instance_id = _service_instance_id
    if service_instance_id is not None:
        provider._reset_service_instance_id(service_instance_id)


def _after_in_child() -> None:
    # ``_lock`` is held across the fork (acquired in ``before``), so we own
    # exclusive access to the registry here and release it once done.
    global _service_instance_id  # noqa: PLW0603
    service_instance_id = str(uuid4())
    _service_instance_id = service_instance_id
    providers = list(_providers)
    _lock.release()
    for provider in providers:
        provider._reset_service_instance_id(service_instance_id)


if hasattr(os, "register_at_fork"):
    # Acquiring ``_lock`` in ``before`` guarantees no other thread holds it
    # while we fork, avoiding a deadlock in the single-threaded child.
    os.register_at_fork(
        before=_lock.acquire,
        after_in_parent=_lock.release,
        after_in_child=_after_in_child,
    )
