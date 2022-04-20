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

# FIXME Find a way to allow mypy to run here.
# Without this mypy fails with the error described here:
# https://github.com/python/mypy/issues/7182
# type: ignore


from opentelemetry._metrics.___init__ import (
    Meter,
    MeterProvider,
    NoOpMeter,
    NoOpMeterProvider,
    get_meter,
    get_meter_provider,
    set_meter_provider,
)

__all__ = [
    "MeterProvider",
    "NoOpMeterProvider",
    "Meter",
    "NoOpMeter",
    "get_meter",
    "set_meter_provider",
    "get_meter_provider",
]
