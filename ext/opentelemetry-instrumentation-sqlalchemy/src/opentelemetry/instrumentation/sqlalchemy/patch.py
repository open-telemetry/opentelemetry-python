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

import sqlalchemy
import wrapt
from wrapt import wrap_function_wrapper as _w

from opentelemetry.instrumentation.sqlalchemy.engine import _wrap_create_engine


def unwrap(obj, attr):
    func = getattr(obj, attr, None)
    if (
        func
        and isinstance(func, wrapt.ObjectProxy)
        and hasattr(func, "__wrapped__")
    ):
        setattr(obj, attr, func.__wrapped__)


def _patch():
    # patch the engine creation function
    _w("sqlalchemy", "create_engine", _wrap_create_engine)
    _w("sqlalchemy.engine", "create_engine", _wrap_create_engine)


def _unpatch():
    unwrap(sqlalchemy, "create_engine")
    unwrap(sqlalchemy.engine, "create_engine")
