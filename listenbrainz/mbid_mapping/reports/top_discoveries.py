import psycopg2
import psycopg2.extras
from psycopg2.errors import OperationalError

import config

#    with psycopg2.connect(config.MBID_MAPPING_DATABASE_URI) as mb_conn:
#    with psycopg2.connect(config.SQLALCHEMY_DATABASE_URI) as lb_conn:

def get_top_discoveries(year):
    """
    """

    with psycopg2.connect(config.TIMESCALE_DATABASE_URI) as lb_conn:
        with lb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as lb_curs:
            query = """SELECT user_name
                            , track_name
                            , data->'track_metadata'->>'artist_name' AS artist_name
                            , data->'track_metadata'->'additional_info'->>'recording_msid'::TEXT AS rec_msid
                            , listened_at
                            , extract(year from to_timestamp(listened_at))::INT AS year
                            , recording_mbid
                         FROM listen
              FULL OUTER JOIN listen_join_listen_mbid_mapping lj
                           ON (data->'track_metadata'->'additional_info'->>'recording_msid')::uuid = lj.recording_msid
              FULL OUTER JOIN listen_mbid_mapping m
                              ON lj.listen_mbid_mapping = m.id
                        WHERE user_name = %s
                     ORDER BY user_name, recording_msid, year"""

            lb_curs.execute(query, ('rob',))

            last_msid = None
            plays = []
            saved_row = None
            top_recordings = {}
            while True:
                row = lb_curs.fetchone()
                if not row:
                    break

                if saved_row is None:
                    saved_row = row

                if row["rec_msid"] != last_msid:
                    if plays is not None and len(plays) > 0 and plays[0] == year:
#                        print("Track %s by %s, %d plays" % (saved_row["track_name"], saved_row["artist_name"], len(plays)))
#                        print("  " + ",".join([ str(p) for p in plays]))
                        top_recordings[saved_row["rec_msid"]] = (saved_row, len(plays))

                    plays = []
                    saved_row = row

                plays.append(row["year"])
                last_msid = row["rec_msid"]

            for msid, data in sorted(top_recordings.items(), key=lambda item: item[1][1], reverse=True)[:50]:
                print("%-30s %-30s %d" % (data[0]["track_name"][:29], data[0]["artist_name"][:29], data[1]))



get_top_discoveries(2021)
