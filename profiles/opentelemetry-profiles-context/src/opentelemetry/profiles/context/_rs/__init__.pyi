# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry.sdk.resources import Resource

def publish_context(resource: Resource) -> bool: ...
