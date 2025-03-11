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
Deprecated: Replaced by `code.file.path`.
"""

CODE_FUNCTION: Final = "code.function"
"""
Deprecated: Replaced by `code.function.name`.
"""

CODE_FUNCTION_NAME: Final = "code.function.name"
"""
The method or function fully-qualified name without arguments. The value should fit the natural representation of the language runtime, which is also likely the same used within `code.stacktrace` attribute value.
Note: Values and format depends on each language runtime, thus it is impossible to provide an exhaustive list of examples.
The values are usually the same (or prefixes of) the ones found in native stack trace representation stored in
`code.stacktrace` without information on arguments.

Examples:

* Java method: `com.example.MyHttpService.serveRequest`
* Java anonymous class method: `com.mycompany.Main$1.myMethod`
* Java lambda method: `com.mycompany.Main$$Lambda/0x0000748ae4149c00.myMethod`
* PHP function: `GuzzleHttp\\Client::transfer
* Go function: `github.com/my/repo/pkg.foo.func5`
* Elixir: `OpenTelemetry.Ctx.new`
* Erlang: `opentelemetry_ctx:new`
* Rust: `playground::my_module::my_cool_func`
* C function: `fopen`.
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
Deprecated: Value should be included in `code.function.name` which is expected to be a fully-qualified name.
"""

CODE_STACKTRACE: Final = "code.stacktrace"
"""
A stacktrace as a string in the natural representation for the language runtime. The representation is identical to [`exception.stacktrace`](/docs/exceptions/exceptions-spans.md#stacktrace-representation).
"""
