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

from enum import Enum
from typing import Final

DB_COLLECTION_NAME: Final = "db.collection.name"
"""
The name of a collection (table, container) within the database.
Note: It is RECOMMENDED to capture the value as provided by the application
without attempting to do any case normalization.

The collection name SHOULD NOT be extracted from `db.query.text`,
when the database system supports query text with multiple collections
in non-batch operations.

For batch operations, if the individual operations are known to have the same
collection name then that collection name SHOULD be used.
"""

DB_NAMESPACE: Final = "db.namespace"
"""
The name of the database, fully qualified within the server address and port.
Note: If a database system has multiple namespace components, they SHOULD be concatenated from the most general to the most specific namespace component, using `|` as a separator between the components. Any missing components (and their associated separators) SHOULD be omitted.
Semantic conventions for individual database systems SHOULD document what `db.namespace` means in the context of that system.
It is RECOMMENDED to capture the value as provided by the application without attempting to do any case normalization.
"""

DB_OPERATION_BATCH_SIZE: Final = "db.operation.batch.size"
"""
The number of queries included in a batch operation.
Note: Operations are only considered batches when they contain two or more operations, and so `db.operation.batch.size` SHOULD never be `1`.
"""

DB_OPERATION_NAME: Final = "db.operation.name"
"""
The name of the operation or command being executed.
Note: It is RECOMMENDED to capture the value as provided by the application
without attempting to do any case normalization.

The operation name SHOULD NOT be extracted from `db.query.text`,
when the database system supports query text with multiple operations
in non-batch operations.

If spaces can occur in the operation name, multiple consecutive spaces
SHOULD be normalized to a single space.

For batch operations, if the individual operations are known to have the same operation name
then that operation name SHOULD be used prepended by `BATCH `,
otherwise `db.operation.name` SHOULD be `BATCH` or some other database
system specific term if more applicable.
"""

DB_QUERY_SUMMARY: Final = "db.query.summary"
"""
Low cardinality summary of a database query.
Note: The query summary describes a class of database queries and is useful
as a grouping key, especially when analyzing telemetry for database
calls involving complex queries.

Summary may be available to the instrumentation through
instrumentation hooks or other means. If it is not available, instrumentations
that support query parsing SHOULD generate a summary following
[Generating query summary](/docs/database/database-spans.md#generating-a-summary-of-the-query)
section.
"""

DB_QUERY_TEXT: Final = "db.query.text"
"""
The database query being executed.
Note: For sanitization see [Sanitization of `db.query.text`](/docs/database/database-spans.md#sanitization-of-dbquerytext).
For batch operations, if the individual operations are known to have the same query text then that query text SHOULD be used, otherwise all of the individual query texts SHOULD be concatenated with separator `; ` or some other database system specific separator if more applicable.
Parameterized query text SHOULD NOT be sanitized. Even though parameterized query text can potentially have sensitive data, by using a parameterized query the user is giving a strong signal that any sensitive data will be passed as parameter values, and the benefit to observability of capturing the static part of the query text by default outweighs the risk.
"""

DB_RESPONSE_STATUS_CODE: Final = "db.response.status_code"
"""
Database response status code.
Note: The status code returned by the database. Usually it represents an error code, but may also represent partial success, warning, or differentiate between various types of successful outcomes.
Semantic conventions for individual database systems SHOULD document what `db.response.status_code` means in the context of that system.
"""

DB_STORED_PROCEDURE_NAME: Final = "db.stored_procedure.name"
"""
The name of a stored procedure within the database.
Note: It is RECOMMENDED to capture the value as provided by the application
without attempting to do any case normalization.

For batch operations, if the individual operations are known to have the same
stored procedure name then that stored procedure name SHOULD be used.
"""

DB_SYSTEM_NAME: Final = "db.system.name"
"""
The database management system (DBMS) product as identified by the client instrumentation.
Note: The actual DBMS may differ from the one identified by the client. For example, when using PostgreSQL client libraries to connect to a CockroachDB, the `db.system.name` is set to `postgresql` based on the instrumentation's best knowledge.
"""


class DbSystemNameValues(Enum):
    OTHER_SQL = "other_sql"
    """Some other SQL database. Fallback only."""
    SOFTWAREAG_ADABAS = "softwareag.adabas"
    """[Adabas (Adaptable Database System)](https://documentation.softwareag.com/?pf=adabas)."""
    ACTIAN_INGRES = "actian.ingres"
    """[Actian Ingres](https://www.actian.com/databases/ingres/)."""
    AWS_DYNAMODB = "aws.dynamodb"
    """[Amazon DynamoDB](https://aws.amazon.com/pm/dynamodb/)."""
    AWS_REDSHIFT = "aws.redshift"
    """[Amazon Redshift](https://aws.amazon.com/redshift/)."""
    AZURE_COSMOSDB = "azure.cosmosdb"
    """[Azure Cosmos DB](https://learn.microsoft.com/azure/cosmos-db)."""
    INTERSYSTEMS_CACHE = "intersystems.cache"
    """[InterSystems Caché](https://www.intersystems.com/products/cache/)."""
    CASSANDRA = "cassandra"
    """[Apache Cassandra](https://cassandra.apache.org/)."""
    CLICKHOUSE = "clickhouse"
    """[ClickHouse](https://clickhouse.com/)."""
    COCKROACHDB = "cockroachdb"
    """[CockroachDB](https://www.cockroachlabs.com/)."""
    COUCHBASE = "couchbase"
    """[Couchbase](https://www.couchbase.com/)."""
    COUCHDB = "couchdb"
    """[Apache CouchDB](https://couchdb.apache.org/)."""
    DERBY = "derby"
    """[Apache Derby](https://db.apache.org/derby/)."""
    ELASTICSEARCH = "elasticsearch"
    """[Elasticsearch](https://www.elastic.co/elasticsearch)."""
    FIREBIRDSQL = "firebirdsql"
    """[Firebird](https://www.firebirdsql.org/)."""
    GCP_SPANNER = "gcp.spanner"
    """[Google Cloud Spanner](https://cloud.google.com/spanner)."""
    GEODE = "geode"
    """[Apache Geode](https://geode.apache.org/)."""
    H2DATABASE = "h2database"
    """[H2 Database](https://h2database.com/)."""
    HBASE = "hbase"
    """[Apache HBase](https://hbase.apache.org/)."""
    HIVE = "hive"
    """[Apache Hive](https://hive.apache.org/)."""
    HSQLDB = "hsqldb"
    """[HyperSQL Database](https://hsqldb.org/)."""
    IBM_DB2 = "ibm.db2"
    """[IBM Db2](https://www.ibm.com/db2)."""
    IBM_INFORMIX = "ibm.informix"
    """[IBM Informix](https://www.ibm.com/products/informix)."""
    IBM_NETEZZA = "ibm.netezza"
    """[IBM Netezza](https://www.ibm.com/products/netezza)."""
    INFLUXDB = "influxdb"
    """[InfluxDB](https://www.influxdata.com/)."""
    INSTANTDB = "instantdb"
    """[Instant](https://www.instantdb.com/)."""
    MARIADB = "mariadb"
    """[MariaDB](https://mariadb.org/)."""
    MEMCACHED = "memcached"
    """[Memcached](https://memcached.org/)."""
    MONGODB = "mongodb"
    """[MongoDB](https://www.mongodb.com/)."""
    MICROSOFT_SQL_SERVER = "microsoft.sql_server"
    """[Microsoft SQL Server](https://www.microsoft.com/sql-server)."""
    MYSQL = "mysql"
    """[MySQL](https://www.mysql.com/)."""
    NEO4J = "neo4j"
    """[Neo4j](https://neo4j.com/)."""
    OPENSEARCH = "opensearch"
    """[OpenSearch](https://opensearch.org/)."""
    ORACLE_DB = "oracle.db"
    """[Oracle Database](https://www.oracle.com/database/)."""
    POSTGRESQL = "postgresql"
    """[PostgreSQL](https://www.postgresql.org/)."""
    REDIS = "redis"
    """[Redis](https://redis.io/)."""
    SAP_HANA = "sap.hana"
    """[SAP HANA](https://www.sap.com/products/technology-platform/hana/what-is-sap-hana.html)."""
    SAP_MAXDB = "sap.maxdb"
    """[SAP MaxDB](https://maxdb.sap.com/)."""
    SQLITE = "sqlite"
    """[SQLite](https://www.sqlite.org/)."""
    TERADATA = "teradata"
    """[Teradata](https://www.teradata.com/)."""
    TRINO = "trino"
    """[Trino](https://trino.io/)."""
