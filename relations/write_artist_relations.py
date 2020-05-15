#!/usr/bin/env python3

import os
import sys
import psycopg2
import ujson
import tarfile
import datetime, time
from time import asctime
import click
from tempfile import mkstemp
import config

DUMP_QUERY = '''SELECT CAST(count AS float) / (select max(count) from relations.artist_artist_relations) as score,
                       a0.gid, a0.name, a1.gid, a1.name
                  FROM relations.artist_artist_relations arr
                  JOIN artist a0 ON arr.artist_0 = a0.id
                  JOIN artist a1 ON arr.artist_1 = a1.id
                 WHERE count > 3
              ORDER BY score DESC
             '''

DUMP_QUERY_AC = '''SELECT CAST(count AS float) / (select max(count) from relations.artist_credit_artist_credit_relations) as score,
                          ac0.id, string_agg(concat(acn0.name, acn0.join_phrase), ''),
                          ac1.id, string_agg(concat(acn1.name, acn1.join_phrase), '')
                     FROM relations.artist_credit_artist_credit_relations arr
                     JOIN artist_credit ac0 ON arr.artist_credit_0 = ac0.id
                     JOIN artist_credit_name acn0 ON arr.artist_credit_0 = acn0.artist_credit
                     JOIN artist_credit ac1 ON arr.artist_credit_1 = ac1.id
                     JOIN artist_credit_name acn1 ON arr.artist_credit_1 = acn1.artist_credit
                    WHERE count > 3
                 GROUP BY ac0.id, acn0.position, ac1.id, acn1.position, arr.count
                 ORDER BY score DESC
                '''

def write_table(use_ac):
    '''
        Write the relations from the table to a temp file. Is use_ac is True, dump the artist_credit_relations table,
        not the artist_relations_table.
    '''

    if use_ac:
        filename = "artist-credit-artist-credit-relations.json"
        tarname = "artist-credit-artist-credit-relations.tar.bz2"
    else:
        filename = "artist-artist-relations.json"
        tarname = "artist-artist-relations.tar.bz2"

    count = 0
    fh, temp_file = mkstemp()
    os.close(fh) # pesky!

    print(asctime(), "writing relations to %s" % temp_file)
    with open(temp_file, "wt") as f:
        with psycopg2.connect(config.DB_CONNECT) as conn:
            with conn.cursor() as curs:
                if use_ac:
                    curs.execute(DUMP_QUERY_AC)
                else:
                    curs.execute(DUMP_QUERY)
                while True:
                    row = curs.fetchone()
                    if not row:
                        break

                    if use_ac:
                        f.write(ujson.dumps({
                            'score' : row[0],
                            'id_0' : row[1],
                            'name_0' : row[2],
                            'id_1' : row[3],
                            'name_1' : row[4]
                        }) + "\n")
                    else:
                        f.write(ujson.dumps({
                            'score' : row[0],
                            'mbid_0' : row[1],
                            'name_0' : row[2],
                            'mbid_1' : row[3],
                            'name_1' : row[4]
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
@click.option('--use-ac', '-a', is_flag=True, default=False)
def write(**opts):
    write_table(opts['use_ac'])


if __name__ == "__main__":
    write()
