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

ORACLE_DB_DOMAIN: Final = "oracle.db.domain"
"""
The database domain associated with the connection.
Note: This attribute SHOULD be set to the value of the `DB_DOMAIN` initialization parameter,
as exposed in `v$parameter`. `DB_DOMAIN` defines the domain portion of the global
database name and SHOULD be configured when a database is, or may become, part of a
distributed environment. Its value consists of one or more valid identifiers
(alphanumeric ASCII characters) separated by periods.
"""

ORACLE_DB_INSTANCE_NAME: Final = "oracle.db.instance.name"
"""
The instance name associated with the connection in an Oracle Real Application Clusters environment.
Note: There can be multiple instances associated with a single database service. It indicates the
unique instance name to which the connection is currently bound. For non-RAC databases, this value
defaults to the `oracle.db.name`.
"""

ORACLE_DB_NAME: Final = "oracle.db.name"
"""
The database name associated with the connection.
Note: This attribute SHOULD be set to the value of the parameter `DB_NAME` exposed in `v$parameter`.
"""

ORACLE_DB_PDB: Final = "oracle.db.pdb"
"""
The pluggable database (PDB) name associated with the connection.
Note: This attribute SHOULD reflect the PDB that the session is currently connected to.
If instrumentation cannot reliably obtain the active PDB name for each operation
without issuing an additional query (such as `SELECT SYS_CONTEXT`), it is
RECOMMENDED to fall back to the PDB name specified at connection establishment.
"""

ORACLE_DB_SERVICE: Final = "oracle.db.service"
"""
The service name currently associated with the database connection.
Note: The effective service name for a connection can change during its lifetime,
for example after executing sql, `ALTER SESSION`. If an instrumentation cannot reliably
obtain the current service name for each operation without issuing an additional
query (such as `SELECT SYS_CONTEXT`), it is RECOMMENDED to fall back to the
service name originally provided at connection establishment.
"""
