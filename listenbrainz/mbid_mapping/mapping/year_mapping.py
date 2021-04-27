import psycopg2
from psycopg2.errors import OperationalError, UndefinedTable
from mapping.utils import create_schema, insert_rows, log
from mapping.formats import create_formats_table
import config


BATCH_SIZE = 5000
TEST_ARTIST_ID = 1160983  # Gun'n'roses, because of obvious spelling issues


def create_tables(mb_conn):
    """
        Create tables needed to create the year mapping. First
        is the temp table that the results will be stored in (in order
        to not conflict with the production version of this table).
        Second its format sort table to enables us to sort releases
        according to preferred format, release date and type.
    """

    # drop/create finished table
    try:
        with mb_conn.cursor() as curs:
            curs.execute("DROP TABLE IF EXISTS mapping.tmp_year_mapping")
            curs.execute("""CREATE TABLE mapping.tmp_year_mapping (
                                         recording_name            TEXT NOT NULL,
                                         artist_credit_name        TEXT NOT NULL,
                                         year                      INTEGER)""")
            curs.execute("DROP TABLE IF EXISTS mapping.tmp_year_mapping_release")
            curs.execute("""CREATE TABLE mapping.tmp_year_mapping_release (
                                            id      SERIAL,
                                            release INTEGER)""")
            create_formats_table(mb_conn)
            mb_conn.commit()
    except (OperationalError, UndefinedTable) as err:
        log("year mapping: failed to create recording pair year tables", err)
        mb_conn.rollback()
        raise


def create_indexes(conn):
    """
        Create indexes for the year mapping
    """

    try:
        with conn.cursor() as curs:
            curs.execute("""CREATE INDEX tmp_year_mapping_idx_ac_rec_year
                                      ON mapping.tmp_year_mapping(artist_credit_name, recording_name)""")
        conn.commit()
    except OperationalError as err:
        log("year mapping: failed to create recording pair index", err)
        conn.rollback()
        raise


def create_temp_release_table(conn):
    """
        Creates an intermediate table that orders releases by types, format,
        releases date, country and artist_credit. This sorting should in theory
        sort the most desired releases (albums, digital releases, first released)
        over the other types in order to match to the "canonical" releases
        and to also ensure that tracks that came from one release
        will be matched to the same release and will not end up being
        scattered across many releases from the same artist.
    """

    with conn.cursor() as curs:
        log("year mapping temp tables: select")
        query = """             SELECT r.id AS release
                                  FROM musicbrainz.release_group rg
                                  JOIN musicbrainz.release r ON rg.id = r.release_group
                             LEFT JOIN musicbrainz.release_country rc ON rc.release = r.id
                                  JOIN musicbrainz.medium m ON m.release = r.id
                                  JOIN musicbrainz.medium_format mf ON m.format = mf.id
                                  JOIN mapping.format_sort fs ON mf.id = fs.format
                                  JOIN musicbrainz.artist_credit ac ON rg.artist_credit = ac.id
                                  JOIN musicbrainz.release_group_primary_type rgpt ON rg.type = rgpt.id
                             LEFT JOIN musicbrainz.release_group_secondary_type_join rgstj ON rg.id = rgstj.release_group
                             LEFT JOIN musicbrainz.release_group_secondary_type rgst ON rgstj.secondary_type = rgst.id
                                       %s
                                 ORDER BY rg.type, rgst.id desc,
                                          to_date(date_year::TEXT || '-' ||
                                                  COALESCE(date_month,12)::TEXT || '-' ||
                                                  COALESCE(date_day,28)::TEXT, 'YYYY-MM-DD'),
                                          country, rg.artist_credit, rg.name"""

        if config.USE_MINIMAL_DATASET:
            log("year mapping temp tables: Using a minimal dataset!")
            curs.execute(query % ('WHERE rg.artist_credit = %d' % TEST_ARTIST_ID))
        else:
            log("year mapping temp tables: Using full dataset")
            curs.execute(query % "")

        # Fetch releases and toss out duplicates -- using DISTINCT in the query above is not possible as it will
        # destroy the sort order we so carefully crafted.
        with conn.cursor() as curs_insert:
            rows = []
            count = 0
            release_index = {}
            for row in curs:
                if row[0] in release_index:
                    continue

                release_index[row[0]] = 1

                count += 1
                rows.append((count, row[0]))

                if len(rows) == BATCH_SIZE:
                    insert_rows(curs_insert, "mapping.tmp_year_mapping_release", rows)
                    rows = []

            if rows:
                insert_rows(curs_insert, "mapping.tmp_year_mapping_release", rows)

        log("year mapping temp tables: done")


def swap_table_and_indexes(conn):
    """
        Swap temp tables and indexes for production tables and indexes.
    """

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
            curs.execute("DROP TABLE IF EXISTS mapping.year_mapping")
            curs.execute("DROP TABLE IF EXISTS mapping.year_mapping_release")
            curs.execute("""ALTER TABLE mapping.tmp_year_mapping_release
                              RENAME TO year_mapping_release""")
            curs.execute("""ALTER TABLE mapping.tmp_year_mapping
                              RENAME TO year_mapping""")

            curs.execute("""ALTER INDEX mapping.tmp_year_mapping_idx_ac_rec_year
                              RENAME TO year_mapping_idx_ac_rec_year""")
        conn.commit()
    except OperationalError as err:
        log("year mapping: failed to swap in new recording pair tables", str(err))
        conn.rollback()
        raise


def create_year_mapping():
    """
        This function is the heart of the recording artist pair year mapping. It
        calculates the intermediate table and then fetches all the recordings
        from these tables so that duplicate recording-artist pairs all
        resolve to the "canonical" release-artist pairs that make
        them suitable for inclusion in the msid-mapping.
    """

    log("year mapping: start")
    with psycopg2.connect(config.DB_CONNECT_MB) as mb_conn:
        with mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:

            # Create the dest table (perhaps dropping the old one first)
            log("year mapping: drop old tables, create new tables")
            create_schema(mb_conn)
            create_tables(mb_conn)

            create_temp_release_table(mb_conn)
            with mb_conn.cursor() as mb_curs2:

                rows = []
                last_ac_id = None
                artist_recordings = {}
                count = 0
                log("year mapping: fetch recordings")
                mb_curs.execute("""SELECT lower(musicbrainz.musicbrainz_unaccent(r.name)) AS recording_name,
                                          lower(musicbrainz.musicbrainz_unaccent(ac.name)) AS artist_credit_name,
                                          ac.id AS artist_credit_id,
                                          date_year AS year
                                     FROM recording r
                                     JOIN artist_credit ac
                                       ON r.artist_credit = ac.id
                                     JOIN artist_credit_name acn
                                       ON ac.id = acn.artist_credit
                                     JOIN track t
                                       ON t.recording = r.id
                                     JOIN medium m
                                       ON m.id = t.medium
                                     JOIN release rl
                                       ON rl.id = m.release
                                     JOIN mapping.tmp_year_mapping_release rpr
                                       ON rl.id = rpr.release
                                LEFT JOIN release_country rc
                                       ON rc.release = rl.id
                                    ORDER BY ac.id, rpr.id""")
                while True:
                    row = mb_curs.fetchone()
                    if not row:
                        break

                    if not last_ac_id:
                        last_ac_id = row['artist_credit_id']

                    if row['artist_credit_id'] != last_ac_id:
                        # insert the rows that made it
                        rows.extend(artist_recordings.values())
                        artist_recordings = {}

                        if len(rows) > BATCH_SIZE:
                            insert_rows(mb_curs2, "mapping.tmp_year_mapping", rows)
                            count += len(rows)
                            mb_conn.commit()
                            rows = []

                    recording_name = row['recording_name']
                    artist_credit_name = row['artist_credit_name']
                    if recording_name not in artist_recordings:
                        artist_recordings[recording_name] = (recording_name.replace("'", "''"),
                                                             artist_credit_name.replace("'", "''"), row['year'])
                    last_ac_id = row['artist_credit_id']

                rows.extend(artist_recordings.values())
                if rows:
                    insert_rows(mb_curs2, "mapping.tmp_year_mapping", rows)
                    mb_conn.commit()
                    count += len(rows)

            log("year mapping: inserted %d rows total." % count)
            create_indexes(mb_conn)

            log("year mapping: swap tables and indexes into production.")
            swap_table_and_indexes(mb_conn)

    log("year mapping: done")
