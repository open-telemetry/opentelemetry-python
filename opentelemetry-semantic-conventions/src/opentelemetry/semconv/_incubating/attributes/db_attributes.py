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

DB_CASSANDRA_CONSISTENCY_LEVEL: Final = "db.cassandra.consistency_level"
"""
The consistency level of the query. Based on consistency values from [CQL](https://docs.datastax.com/en/cassandra-oss/3.0/cassandra/dml/dmlConfigConsistency.html).
"""

DB_CASSANDRA_COORDINATOR_DC: Final = "db.cassandra.coordinator.dc"
"""
The data center of the coordinating node for a query.
"""

DB_CASSANDRA_COORDINATOR_ID: Final = "db.cassandra.coordinator.id"
"""
The ID of the coordinating node for a query.
"""

DB_CASSANDRA_IDEMPOTENCE: Final = "db.cassandra.idempotence"
"""
Whether or not the query is idempotent.
"""

DB_CASSANDRA_PAGE_SIZE: Final = "db.cassandra.page_size"
"""
The fetch size used for paging, i.e. how many rows will be returned at once.
"""

DB_CASSANDRA_SPECULATIVE_EXECUTION_COUNT: Final = (
    "db.cassandra.speculative_execution_count"
)
"""
The number of times a query was speculatively executed. Not set or `0` if the query was not executed speculatively.
"""

DB_CASSANDRA_TABLE: Final = "db.cassandra.table"
"""
The name of the primary Cassandra table that the operation is acting upon, including the keyspace name (if applicable).
Note: This mirrors the db.sql.table attribute but references cassandra rather than sql. It is not recommended to attempt any client-side parsing of `db.statement` just to get this property, but it should be set if it is provided by the library being instrumented. If the operation is acting upon an anonymous table, or more than one table, this value MUST NOT be set.
"""

DB_CONNECTION_STRING: Final = "db.connection_string"
"""
Deprecated: "Replaced by `server.address` and `server.port`.".
"""

DB_COSMOSDB_CLIENT_ID: Final = "db.cosmosdb.client_id"
"""
Unique Cosmos client instance id.
"""

DB_COSMOSDB_CONNECTION_MODE: Final = "db.cosmosdb.connection_mode"
"""
Cosmos client connection mode.
"""

DB_COSMOSDB_CONTAINER: Final = "db.cosmosdb.container"
"""
Cosmos DB container name.
"""

DB_COSMOSDB_OPERATION_TYPE: Final = "db.cosmosdb.operation_type"
"""
CosmosDB Operation Type.
"""

DB_COSMOSDB_REQUEST_CHARGE: Final = "db.cosmosdb.request_charge"
"""
RU consumed for that operation.
"""

DB_COSMOSDB_REQUEST_CONTENT_LENGTH: Final = (
    "db.cosmosdb.request_content_length"
)
"""
Request payload size in bytes.
"""

DB_COSMOSDB_STATUS_CODE: Final = "db.cosmosdb.status_code"
"""
Cosmos DB status code.
"""

DB_COSMOSDB_SUB_STATUS_CODE: Final = "db.cosmosdb.sub_status_code"
"""
Cosmos DB sub status code.
"""

DB_ELASTICSEARCH_CLUSTER_NAME: Final = "db.elasticsearch.cluster.name"
"""
Represents the identifier of an Elasticsearch cluster.
"""

DB_ELASTICSEARCH_NODE_NAME: Final = "db.elasticsearch.node.name"
"""
Deprecated: Replaced by `db.instance.id`.
"""

DB_ELASTICSEARCH_PATH_PARTS_TEMPLATE: Final = "db.elasticsearch.path_parts"
"""
A dynamic value in the url path.
Note: Many Elasticsearch url paths allow dynamic values. These SHOULD be recorded in span attributes in the format `db.elasticsearch.path_parts.<key>`, where `<key>` is the url path part name. The implementation SHOULD reference the [elasticsearch schema](https://raw.githubusercontent.com/elastic/elasticsearch-specification/main/output/schema/schema.json) in order to map the path part values to their names.
"""

DB_INSTANCE_ID: Final = "db.instance.id"
"""
An identifier (address, unique name, or any other identifier) of the database instance that is executing queries or mutations on the current connection. This is useful in cases where the database is running in a clustered environment and the instrumentation is able to record the node executing the query. The client may obtain this value in databases like MySQL using queries like `select @@hostname`.
"""

DB_JDBC_DRIVER_CLASSNAME: Final = "db.jdbc.driver_classname"
"""
Deprecated: Removed as not used.
"""

DB_MONGODB_COLLECTION: Final = "db.mongodb.collection"
"""
The MongoDB collection being accessed within the database stated in `db.name`.
"""

DB_MSSQL_INSTANCE_NAME: Final = "db.mssql.instance_name"
"""
The Microsoft SQL Server [instance name](https://docs.microsoft.com/sql/connect/jdbc/building-the-connection-url?view=sql-server-ver15) connecting to. This name is used to determine the port of a named instance.
Note: If setting a `db.mssql.instance_name`, `server.port` is no longer required (but still recommended if non-standard).
"""

DB_NAME: Final = "db.name"
"""
This attribute is used to report the name of the database being accessed. For commands that switch the database, this should be set to the target database (even if the command fails).
Note: In some SQL databases, the database name to be used is called "schema name". In case there are multiple layers that could be considered for database name (e.g. Oracle instance name and schema name), the database name to be used is the more specific layer (e.g. Oracle schema name).
"""

DB_OPERATION: Final = "db.operation"
"""
The name of the operation being executed, e.g. the [MongoDB command name](https://docs.mongodb.com/manual/reference/command/#database-operations) such as `findAndModify`, or the SQL keyword.
Note: When setting this to an SQL keyword, it is not recommended to attempt any client-side parsing of `db.statement` just to get this property, but it should be set if the operation name is provided by the library being instrumented. If the SQL statement has an ambiguous operation, or performs more than one operation, this value may be omitted.
"""

DB_REDIS_DATABASE_INDEX: Final = "db.redis.database_index"
"""
The index of the database being accessed as used in the [`SELECT` command](https://redis.io/commands/select), provided as an integer. To be used instead of the generic `db.name` attribute.
"""

DB_SQL_TABLE: Final = "db.sql.table"
"""
The name of the primary table that the operation is acting upon, including the database name (if applicable).
Note: It is not recommended to attempt any client-side parsing of `db.statement` just to get this property, but it should be set if it is provided by the library being instrumented. If the operation is acting upon an anonymous table, or more than one table, this value MUST NOT be set.
"""

DB_STATEMENT: Final = "db.statement"
"""
The database statement being executed.
"""

DB_SYSTEM: Final = "db.system"
"""
An identifier for the database management system (DBMS) product being used. See below for a list of well-known identifiers.
"""

DB_USER: Final = "db.user"
"""
Username for accessing the database.
"""


class DbCassandraConsistencyLevelValues(Enum):
    ALL: Final = "all"
    """all."""
    EACH_QUORUM: Final = "each_quorum"
    """each_quorum."""
    QUORUM: Final = "quorum"
    """quorum."""
    LOCAL_QUORUM: Final = "local_quorum"
    """local_quorum."""
    ONE: Final = "one"
    """one."""
    TWO: Final = "two"
    """two."""
    THREE: Final = "three"
    """three."""
    LOCAL_ONE: Final = "local_one"
    """local_one."""
    ANY: Final = "any"
    """any."""
    SERIAL: Final = "serial"
    """serial."""
    LOCAL_SERIAL: Final = "local_serial"
    """local_serial."""


class DbCosmosdbConnectionModeValues(Enum):
    GATEWAY: Final = "gateway"
    """Gateway (HTTP) connections mode."""
    DIRECT: Final = "direct"
    """Direct connection."""


class DbCosmosdbOperationTypeValues(Enum):
    INVALID: Final = "Invalid"
    """invalid."""
    CREATE: Final = "Create"
    """create."""
    PATCH: Final = "Patch"
    """patch."""
    READ: Final = "Read"
    """read."""
    READ_FEED: Final = "ReadFeed"
    """read_feed."""
    DELETE: Final = "Delete"
    """delete."""
    REPLACE: Final = "Replace"
    """replace."""
    EXECUTE: Final = "Execute"
    """execute."""
    QUERY: Final = "Query"
    """query."""
    HEAD: Final = "Head"
    """head."""
    HEAD_FEED: Final = "HeadFeed"
    """head_feed."""
    UPSERT: Final = "Upsert"
    """upsert."""
    BATCH: Final = "Batch"
    """batch."""
    QUERY_PLAN: Final = "QueryPlan"
    """query_plan."""
    EXECUTE_JAVASCRIPT: Final = "ExecuteJavaScript"
    """execute_javascript."""


class DbSystemValues(Enum):
    OTHER_SQL: Final = "other_sql"
    """Some other SQL database. Fallback only. See notes."""
    MSSQL: Final = "mssql"
    """Microsoft SQL Server."""
    MSSQLCOMPACT: Final = "mssqlcompact"
    """Microsoft SQL Server Compact."""
    MYSQL: Final = "mysql"
    """MySQL."""
    ORACLE: Final = "oracle"
    """Oracle Database."""
    DB2: Final = "db2"
    """IBM Db2."""
    POSTGRESQL: Final = "postgresql"
    """PostgreSQL."""
    REDSHIFT: Final = "redshift"
    """Amazon Redshift."""
    HIVE: Final = "hive"
    """Apache Hive."""
    CLOUDSCAPE: Final = "cloudscape"
    """Cloudscape."""
    HSQLDB: Final = "hsqldb"
    """HyperSQL DataBase."""
    PROGRESS: Final = "progress"
    """Progress Database."""
    MAXDB: Final = "maxdb"
    """SAP MaxDB."""
    HANADB: Final = "hanadb"
    """SAP HANA."""
    INGRES: Final = "ingres"
    """Ingres."""
    FIRSTSQL: Final = "firstsql"
    """FirstSQL."""
    EDB: Final = "edb"
    """EnterpriseDB."""
    CACHE: Final = "cache"
    """InterSystems Caché."""
    ADABAS: Final = "adabas"
    """Adabas (Adaptable Database System)."""
    FIREBIRD: Final = "firebird"
    """Firebird."""
    DERBY: Final = "derby"
    """Apache Derby."""
    FILEMAKER: Final = "filemaker"
    """FileMaker."""
    INFORMIX: Final = "informix"
    """Informix."""
    INSTANTDB: Final = "instantdb"
    """InstantDB."""
    INTERBASE: Final = "interbase"
    """InterBase."""
    MARIADB: Final = "mariadb"
    """MariaDB."""
    NETEZZA: Final = "netezza"
    """Netezza."""
    PERVASIVE: Final = "pervasive"
    """Pervasive PSQL."""
    POINTBASE: Final = "pointbase"
    """PointBase."""
    SQLITE: Final = "sqlite"
    """SQLite."""
    SYBASE: Final = "sybase"
    """Sybase."""
    TERADATA: Final = "teradata"
    """Teradata."""
    VERTICA: Final = "vertica"
    """Vertica."""
    H2: Final = "h2"
    """H2."""
    COLDFUSION: Final = "coldfusion"
    """ColdFusion IMQ."""
    CASSANDRA: Final = "cassandra"
    """Apache Cassandra."""
    HBASE: Final = "hbase"
    """Apache HBase."""
    MONGODB: Final = "mongodb"
    """MongoDB."""
    REDIS: Final = "redis"
    """Redis."""
    COUCHBASE: Final = "couchbase"
    """Couchbase."""
    COUCHDB: Final = "couchdb"
    """CouchDB."""
    COSMOSDB: Final = "cosmosdb"
    """Microsoft Azure Cosmos DB."""
    DYNAMODB: Final = "dynamodb"
    """Amazon DynamoDB."""
    NEO4J: Final = "neo4j"
    """Neo4j."""
    GEODE: Final = "geode"
    """Apache Geode."""
    ELASTICSEARCH: Final = "elasticsearch"
    """Elasticsearch."""
    MEMCACHED: Final = "memcached"
    """Memcached."""
    COCKROACHDB: Final = "cockroachdb"
    """CockroachDB."""
    OPENSEARCH: Final = "opensearch"
    """OpenSearch."""
    CLICKHOUSE: Final = "clickhouse"
    """ClickHouse."""
    SPANNER: Final = "spanner"
    """Cloud Spanner."""
    TRINO: Final = "trino"
    """Trino."""
