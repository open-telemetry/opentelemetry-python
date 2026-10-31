# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Bucket storage and index mappings for the exponential histogram.

``buckets`` holds the counts of one data point, and the ``mapping``
subpackage turns a measured value into the bucket index those counts are
addressed by. The aggregation that drives both lives in
``opentelemetry.sdk.metrics._internal.aggregation``.
"""
