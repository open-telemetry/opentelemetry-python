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


# DefaultMaxSize is the default maximum number of buckets per positive or
# negative number range.  The value 160 is specified by OpenTelemetry--yields a
# maximum relative error of less than 5% for data with contrast 10**5 (e.g.,
# latencies in the range 1ms to 100s).
# See the derivation here:
# https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/sdk.md#exponential-bucket-histogram-aggregation)

DEFAULT_MAX_SIZE = 160

# MinSize is the smallest reasonable configuration, which is small enough to
# contain the entire normal floating point range at MinScale.
MIN_MAX_SIZE = 2

# MaximumMaxSize is an arbitrary limit meant to limit accidental use
# of giant histograms.
MAX_MAX_SIZE = 16384
