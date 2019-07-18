# Copyright 2019, OpenTelemetry Authors
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

from .base_context import BaseRuntimeContext

__all__ = ['Context']

Context: BaseRuntimeContext = None

try:
    from .async_context import AsyncRuntimeContext
    Context = AsyncRuntimeContext()  # pylint:disable=invalid-name
except ImportError:
    from .thread_local_context import ThreadLocalRuntimeContext
    Context = ThreadLocalRuntimeContext()  # pylint:disable=invalid-name
