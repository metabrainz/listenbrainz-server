#!/usr/bin/env python3

import os
import tarfile
import datetime
import time
from time import asctime
from tempfile import mkstemp

import click
import psycopg2
import ujson
import config


DUMP_QUERY = '''SELECT CAST(count AS float) / (select max(count) from relations.artist_artist_relations) as score,
                       a0.gid, a0.name, a1.gid, a1.name
                  FROM relations.artist_artist_relations arr
                  JOIN artist a0 ON arr.artist_0 = a0.id
                  JOIN artist a1 ON arr.artist_1 = a1.id
              ORDER BY score DESC
             '''

DUMP_QUERY_AC = '''SELECT CAST(count AS float) / (SELECT MAX(count)
                                                    FROM relations.artist_credit_artist_credit_relations) AS score,
                          ac0.id, ac0.name,
                          ac1.id, ac1.name
                     FROM relations.artist_credit_artist_credit_relations arr
                     JOIN artist_credit ac0 ON arr.artist_credit_0 = ac0.id
                     JOIN artist_credit ac1 ON arr.artist_credit_1 = ac1.id
                 ORDER BY score DESC
                '''

def write_table(write_artist):
    '''
        Write the relations from the table to a temp file. Is write_artist is True, dump the artist_relations table,
        not the artist_relations_table.
    '''

    dt = datetime.datetime.now()
    date_string = "%d-%02d-%02d" % (dt.year, dt.month, dt.day)
    if write_artist:
        filename = "artist-artist-relations.json"
        tarname = "artist-artist-relations.%s.tar.bz2" % date_string
    else:
        filename = "artist_credit-artist_credit-relations.json"
        tarname = "artist_credit-artist_credit-relations.%s.tar.bz2" % date_string

    fh, temp_file = mkstemp()
    os.close(fh)  # pesky!

    print(asctime(), "writing relations to %s" % temp_file)
    with open(temp_file, "wt") as f:
        with psycopg2.connect(config.DB_CONNECT) as conn:
            with conn.cursor() as curs:
                if write_artist:
                    curs.execute(DUMP_QUERY)
                else:
                    curs.execute(DUMP_QUERY_AC)
                while True:
                    row = curs.fetchone()
                    if not row:
                        break

                    if write_artist:
                        f.write(ujson.dumps({
                            'score': row[0],
                            'mbid_0': row[1],
                            'name_0': row[2],
                            'mbid_1': row[3],
                            'name_1': row[4]
                        }) + "\n")
                    else:
                        f.write(ujson.dumps({
                            'score': row[0],
                            'id_0': row[1],
                            'name_0': row[2],
                            'id_1': row[3],
                            'name_1': row[4]
                        }) + "\n")

    print(asctime(), "create tar file...")
    with tarfile.open(tarname, "w:bz2") as tf:
        tf.add(temp_file, os.path.join('mbdump', filename))
        tf.add('../listenbrainz/db/licenses/COPYING-PublicDomain', 'COPYING')
        tf.add('data_dump_files/README', 'README')

        os.unlink(temp_file)

        with open(temp_file, "wt") as f:
            utc_offset_sec = time.altzone if time.localtime().tm_isdst else time.timezone
            utc_offset = datetime.timedelta(seconds=-utc_offset_sec)
            f.write(datetime.datetime.now().replace(tzinfo=datetime.timezone(offset=utc_offset)).isoformat())
            f.write("\n")

        tf.add(temp_file, 'TIMESTAMP')
        os.unlink(temp_file)

    print(asctime(), "done!")


@click.command()
@click.option('--write-artist', '-a', is_flag=True, default=False)
def write(**opts):
    write_table(opts['write_artist'])


if __name__ == "__main__":
    write()
