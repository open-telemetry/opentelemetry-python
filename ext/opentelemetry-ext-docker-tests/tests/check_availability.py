# Copyright 2020, OpenTelemetry Authors
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
import os
import sys
import time

import psycopg2

POSTGRES_HOST = os.getenv("POSTGRESQL_HOST ", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRESQL_PORT ", "5432"))
POSTGRES_DB_NAME = os.getenv("POSTGRESQL_DB_NAME ", "opentelemetry-tests")
POSTGRES_PASSWORD = os.getenv("POSTGRESQL_HOST ", "testpassword")
POSTGRES_USER = os.getenv("POSTGRESQL_HOST ", "testuser")


def check_postgres_connection():
    # Try to connect to DB
    for i in range(5):
        try:
            connection = psycopg2.connect(
                dbname=POSTGRES_DB_NAME,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
            )
            connection.close()
            break
        except Exception as err:
            print(err)
        time.sleep(5)
    else:
        raise Exception("Failed to connect to Postgres DB")


def check_docker_services_availability():
    try:
        print("Checking Postgres availability")
        check_postgres_connection()
    except Exception:
        sys.exit(1)
    sys.exit(0)


check_docker_services_availability()
