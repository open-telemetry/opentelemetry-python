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

from typing import Final

CODE_COLUMN: Final = "code.column"
"""
Deprecated: Replaced by `code.column.number`.
"""

CODE_COLUMN_NUMBER: Final = "code.column.number"
"""
The column number in `code.file.path` best representing the operation. It SHOULD point within the code unit named in `code.function.name`.
"""

CODE_FILE_PATH: Final = "code.file.path"
"""
The source code file name that identifies the code unit as uniquely as possible (preferably an absolute file path).
"""

CODE_FILEPATH: Final = "code.filepath"
"""
Deprecated, use `code.file.path` instead.
"""

CODE_FUNCTION: Final = "code.function"
"""
Deprecated: Replaced by `code.function.name`.
"""

CODE_FUNCTION_NAME: Final = "code.function.name"
"""
The method or function name, or equivalent (usually rightmost part of the code unit's name).
"""

CODE_LINE_NUMBER: Final = "code.line.number"
"""
The line number in `code.file.path` best representing the operation. It SHOULD point within the code unit named in `code.function.name`.
"""

CODE_LINENO: Final = "code.lineno"
"""
Deprecated: Replaced by `code.line.number`.
"""

CODE_NAMESPACE: Final = "code.namespace"
"""
The "namespace" within which `code.function.name` is defined. Usually the qualified class or module name, such that `code.namespace` + some separator + `code.function.name` form a unique identifier for the code unit.
"""

CODE_STACKTRACE: Final = "code.stacktrace"
"""
A stacktrace as a string in the natural representation for the language runtime. The representation is to be determined and documented by each language SIG.
"""
