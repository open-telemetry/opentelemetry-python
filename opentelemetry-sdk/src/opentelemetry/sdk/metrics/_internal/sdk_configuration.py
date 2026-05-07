# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=unused-import

from dataclasses import dataclass
from typing import Sequence

# This kind of import is needed to avoid Sphinx errors.
import opentelemetry.sdk.metrics
import opentelemetry.sdk.resources


@dataclass
class SdkConfiguration:
    exemplar_filter: "opentelemetry.sdk.metrics.ExemplarFilter"
    resource: "opentelemetry.sdk.resources.Resource"
    metric_readers: Sequence["opentelemetry.sdk.metrics.export.MetricReader"]
    views: Sequence["opentelemetry.sdk.metrics.view.View"]
