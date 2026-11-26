"""Fan out accepted listen changes to materialized views for live stats tables."""
from contextlib import closing, contextmanager
from uuid import uuid4

from listenbrainz.clickhouse.query_worker.client import ClickHouseConnection
from listenbrainz.clickhouse.query_worker.listens.aggregate_tables import (
    ARTIST_METADATA, DAILY_ARTIST_COUNTS, HOURLY_COUNTS, LISTEN_AGGREGATES, ListenAggregate,
)


LIVE_STREAM = "listen_changes"


def _source_columns():
    return ", ".join(dict.fromkeys(col for table in LISTEN_AGGREGATES for col in table.source_columns))


def _target(stream, table):
    return table.name if stream == LIVE_STREAM else f"{stream}_{table.name}"


def _drop(client, name):
    client.command(f"DROP TABLE IF EXISTS {name} SETTINGS max_table_size_to_drop = 0")


def _create_stream(client, stream, source):
    # The stream stores no rows. ClickHouse sends the same inserted block to each dependent view.
    client.command(f"CREATE TABLE {stream} ENGINE = Null AS SELECT {_source_columns()}, toInt8(1) AS delta "
                   f"FROM {source} LIMIT 0")


def attach_source(client, source, stream):
    client.command(f"CREATE MATERIALIZED VIEW {source}_to_changes TO {stream} AS "
                   f"SELECT {_source_columns()}, toInt8(1) AS delta FROM {source}")


@contextmanager
def staged_source(client, source, stream):
    attach_source(client, source, stream)
    try:
        yield
    finally:
        _drop(client, source + "_to_changes")


def _artist_lookup(stream):
    return "artist_lookup" if stream == LIVE_STREAM else stream + "_artist_lookup"


def _snapshot_artist_lookup(client, name):
    """Keep the same artist IDs for inserts and deletions until the next full build."""
    client.command(f"""
        CREATE TABLE {name} (mbid String, mb_artist_id Nullable(Int32), canonical_name Nullable(String))
        ENGINE = Join(ANY, LEFT, mbid)
    """)
    if client.command("EXISTS TABLE artist_metadata_cache"):
        client.command(f"INSERT INTO {name} SELECT toString(artist_mbid), artist_id, artist_name "
                       "FROM artist_metadata_cache")


def _attach_aggregate(client, stream, table):
    target = _target(stream, table)
    select = table.select.format(source=stream, artist_lookup=_artist_lookup(stream))
    client.command(f"CREATE MATERIALIZED VIEW {target}_mv TO {target} AS {select}")


def _create_target(client, stream, table):
    client.command(f"CREATE TABLE {_target(stream, table)} ({table.columns}) ENGINE = {table.engine}")


def send_changes(client, stream, source, sign, where="1", parameters=None):
    # During full replacement the old live stream can still have only the
    # hourly columns. Retract deletes using the schema it actually accepts.
    columns = ", ".join(name for (name,) in client.query(
        "SELECT name FROM system.columns WHERE database = currentDatabase() AND table = {stream:String} "
        "AND name != 'delta' ORDER BY position", parameters={"stream": stream},
    ).result_rows)
    client.command(f"INSERT INTO {stream} ({columns}, delta) SELECT {columns}, toInt8({sign}) "
                   f"FROM {source} WHERE {where}", parameters=parameters)


def ensure_aggregates(client):
    """Initialize the change stream and backfill missing aggregate tables together."""
    objects = {name for (name,) in client.query(
        "SELECT name FROM system.tables WHERE database = currentDatabase()"
    ).result_rows}
    missing_stream = not {LIVE_STREAM, "listens_to_changes"} <= objects
    missing = {table for table in LISTEN_AGGREGATES
               if missing_stream or not {table.name, table.name + "_mv"} <= objects}
    # The counts and their labels must use the same MusicBrainz lookup generation.
    if missing.intersection((DAILY_ARTIST_COUNTS, ARTIST_METADATA)) or _artist_lookup(LIVE_STREAM) not in objects:
        missing.update((DAILY_ARTIST_COUNTS, ARTIST_METADATA))
    if HOURLY_COUNTS not in missing and client.command("""
        SELECT count() FROM system.columns WHERE database = currentDatabase()
          AND table = 'hourly_listen_counts' AND name = 'midnight_listen_count'
    """):
        # Keep existing hourly totals while upgrading the view and its target.
        client.command("ALTER TABLE hourly_listen_counts_mv MODIFY QUERY "
                       + HOURLY_COUNTS.select.format(source=LIVE_STREAM))
        client.command("ALTER TABLE hourly_listen_counts DROP COLUMN midnight_listen_count")
    if not missing:
        return

    _drop(client, "listens_to_changes")
    for table in LISTEN_AGGREGATES:
        _drop(client, table.name + "_mv")
        # Remove the old write target when upgrading from separate live and published tables.
        legacy = f"{LIVE_STREAM}_{table.name}"
        if legacy + "_mv" in objects:
            _drop(client, legacy + "_mv")
        if legacy in objects:
            _drop(client, legacy)
    _drop(client, LIVE_STREAM)
    _create_stream(client, LIVE_STREAM, "listens")
    if DAILY_ARTIST_COUNTS in missing:
        lookup = _artist_lookup(LIVE_STREAM)
        _drop(client, lookup)
        _snapshot_artist_lookup(client, lookup)
    for table in missing:
        _drop(client, table.name)
        _create_target(client, LIVE_STREAM, table)
        _attach_aggregate(client, LIVE_STREAM, table)
    send_changes(client, LIVE_STREAM, "listens", 1)
    for table in LISTEN_AGGREGATES:
        if table not in missing:
            _attach_aggregate(client, LIVE_STREAM, table)
    attach_source(client, "listens", LIVE_STREAM)


@contextmanager
def full_dump_aggregates(client, source):
    """Accumulate a full replacement privately while the Parquet files are loaded."""
    stream = source + "_changes"
    _create_stream(client, stream, source)
    try:
        _snapshot_artist_lookup(client, _artist_lookup(stream))
        for table in LISTEN_AGGREGATES:
            _create_target(client, stream, table)
            _attach_aggregate(client, stream, table)
        yield stream
    finally:
        for table in LISTEN_AGGREGATES:
            _drop(client, _target(stream, table) + "_mv")
            _drop(client, _target(stream, table))
        _drop(client, _artist_lookup(stream))
        _drop(client, stream)


def replace_live_aggregates(client, staged_stream, staged_listens):
    """Detach the source until all targets and listens have been published.

    The missing source view is the durable marker for an interrupted publication.
    ensure_aggregates rebuilds every target from the authoritative listens in that case.
    """
    objects = {row[0] for row in client.query(
        "SELECT name FROM system.tables WHERE database = currentDatabase()"
    ).result_rows}
    _drop(client, "listens_to_changes")
    for table in LISTEN_AGGREGATES:
        _drop(client, table.name + "_mv")
    _drop(client, LIVE_STREAM)
    _create_stream(client, LIVE_STREAM, staged_listens)

    targets = [(_artist_lookup(staged_stream), _artist_lookup(LIVE_STREAM))]
    targets.extend((_target(staged_stream, table), table.name) for table in LISTEN_AGGREGATES)
    for staged, live in targets:
        if live in objects:
            client.command(f"EXCHANGE TABLES {staged} AND {live}")
        else:
            client.command(f"RENAME TABLE {staged} TO {live}")
    for table in LISTEN_AGGREGATES:
        _attach_aggregate(client, LIVE_STREAM, table)


def recover_publication(client):
    if not client.command("EXISTS TABLE listens_to_changes"):
        ensure_aggregates(client)


@contextmanager
def aggregate_snapshot(table: ListenAggregate):
    """Pin one live aggregate across the queries of a stats job."""
    connection = ClickHouseConnection.from_config()
    with closing(connection.connect(session_id=uuid4().hex, settings={"session_timeout": 3600},
                                    send_receive_timeout=7200)) as client:
        recover_publication(client)
        client.command(f"CREATE TEMPORARY TABLE stats_snapshot CLONE AS {table.name} ENGINE = {table.engine}")
        try:
            yield client
        finally:
            client.command("DROP TEMPORARY TABLE IF EXISTS stats_snapshot")
