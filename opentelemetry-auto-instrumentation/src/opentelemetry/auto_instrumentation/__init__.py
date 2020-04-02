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

"""
Usage
-----

This package provides a command that automatically instruments a program:

::

    opentelemetry-auto-instrumentation program.py

The code in ``program.py`` needs to use one of the packages for which there is
an OpenTelemetry extension. For a list of the available extensions please check
`here <https://opentelemetry-python.readthedocs.io/>`_.
"""
