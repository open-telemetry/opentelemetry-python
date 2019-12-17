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


class ContextKeys:
    """ TODO """

    EXTRACT_SPAN_CONTEXT_KEY = "extracted-span-context"
    SPAN_KEY = "current-span"

    @classmethod
    def span_context_key(cls) -> str:
        """ TODO """
        return cls.EXTRACT_SPAN_CONTEXT_KEY

    @classmethod
    def span_key(cls) -> str:
        """ TODO """
        return cls.SPAN_KEY
