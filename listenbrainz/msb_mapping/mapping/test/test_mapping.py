import sys
import re
import csv
import psycopg2
import psycopg2.extras
import config


def _read_test_data(filename):
    data = []
    with open(filename, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for row in reader:
            if not row:
                if config.USE_MINIMAL_DATASET:
                    break
                else:

                    continue
            if config.REMOVE_NON_WORD_CHARS:
                row[0] = re.sub(r'\W+', '', row[0])

                row[1] = re.sub(r'\W+', '', row[1])
            data.append(row)

    return data


def test_mapping():
    ''' This test will actually run as many test as there are in the CSV file '''

    data = _read_test_data("mapping/test/mapping_test_cases.csv")

    passed = 0
    failed = 0

    with psycopg2.connect(config.DB_CONNECT_MB) as mb_conn:
        with mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
            for rdata in data:
                curs.execute("""SELECT mb_release_id AS release_id,
                                       rl.gid AS release_mbid,
                                       mb_recording_id AS recording_id,
                                       r.gid AS recording_mbid
                                  FROM mapping.msid_mbid_mapping m
                                  JOIN musicbrainz.release rl
                                    ON mb_release_id = rl.id
                                  JOIN musicbrainz.recording r
                                    ON mb_recording_id = r.id
                                 WHERE msb_artist_name = %s
                                   AND msb_recording_name = %s""", (rdata[1], rdata[0]))
                row = curs.fetchone()
                if not row:
                    print("no match for '%s' '%s'" % (rdata[0], rdata[1]))
                    failed += 1
                    continue

                if row['release_mbid'] != rdata[2]:
                    print("'%s' '%s' expected %s, got %s rel %s rec %s" % (rdata[0], rdata[1], rdata[2], row['release_mbid'],
                          row['release_mbid'], row['recording_mbid']))
                    failed += 1
                else:
                    print("'%s' '%s' ok" % (rdata[0], rdata[1]))
                    passed += 1

    print("%d passed, %d failed." % (passed, failed))
