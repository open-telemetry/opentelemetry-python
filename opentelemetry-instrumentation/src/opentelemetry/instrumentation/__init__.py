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

This package provides a couple of commands that help automatically instruments a program:

opentelemetry-instrument
-----------------------------------

::

    opentelemetry-instrument python program.py

The code in ``program.py`` needs to use one of the packages for which there is
an OpenTelemetry integration. For a list of the available integrations please
check :doc:`here <../../index>`.


opentelemetry-bootstrap
------------------------

::

    opentelemetry-bootstrap --action=install|requirements

This commands inspects the active Python site-packages and figures out which
instrumentation packages the user might want to install. By default it prints out
a list of the suggested instrumentation packages which can be added to a requirements.txt
file. It also supports installing the suggested packages when run with :code:`--action=install`
flag.
"""
