# ClickHouse tests

Run `./test.sh clickhouse` from the repository root. This uses the backend test
image and starts ClickHouse 25.3 alongside the existing TimescaleDB and CouchDB
test services. The same tests are collected by `./test.sh` in CI. As with the
server configuration, create `clickhouse/config.py` from `clickhouse/config.py.sample`
if it does not exist yet.

Database tests fail if a required service is unavailable. Each test creates a
unique ClickHouse database; deletion tests also create an isolated PostgreSQL
schema using the production deletion table definitions. Result handler tests
use a unique CouchDB database prefix. Cleanup removes only that test's data.

The activity tests load `listenbrainz_spark/testdata/full-dump-1` and incremental
dumps 2 and 3 with the real Parquet loader. They compare results with Spark's
saved daily/listening activity JSON files and independently count fixture rows
for all nine ranges. Other tests cover cache reuse and rollover, deletions and
re-submissions, dump replay, failed imports, schema migration, import history,
and persistence through the request and result handlers into CouchDB.

FTP tests replace the network transport or archive download boundary, while
extraction, checksums, file handling and database operations execute normally.
Broker failure tests retain mocks to exercise error handling. Database clients,
SQL results, cache managers and CouchDB writes are not mocked.

To use existing test services outside Compose, set `CLICKHOUSE_TEST_HOST`,
`CLICKHOUSE_TEST_PORT`, `CLICKHOUSE_TEST_USERNAME`, `CLICKHOUSE_TEST_PASSWORD`,
`CLICKHOUSE_TEST_LISTENS_DSN`, and `CLICKHOUSE_TEST_COUCHDB_HOST/PORT/USER/PASSWORD`
as needed. Run `pytest clickhouse listenbrainz/clickhouse/tests` in an environment
with the backend development dependencies installed.
