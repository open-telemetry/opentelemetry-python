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


class LabelKey:
    """The label keys associated with the metric.

    :type key: str
    :param key: the key for the label

    :type description: str
    :param description: description of the label
    """
    def __init__(self,
                 key: str,
                 description: str) -> None:
        self.key = key
        self.description = description
