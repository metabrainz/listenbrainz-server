import sys
import re
import csv
import psycopg2
import config


TEST_MAPPING_QUERY = '''
    SELECT m.mb_release_id
      FROM mapping.msid_mbid_mapping m
     WHERE msb_artist_name = %s 
       AND msb_recording_name = %s
'''

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


def get_mbid_for_release_id(curs, release_id):
    curs.execute("SELECT gid FROM release WHERE id = %d" % release_id)
    row = curs.fetchone()
    return row[0]


def test_mapping():
    ''' This test will actually run as many test as there are in the CSV file '''

    data = _read_test_data("mapping/test/mapping_test_cases.csv")

    passed = 0
    failed = 0

    with psycopg2.connect(config.DB_CONNECT_MB) as mb_conn:
        with mb_conn.cursor() as mb_curs:
            with psycopg2.connect(config.DB_CONNECT_MB) as conn:
                with conn.cursor() as curs:
                    for rdata in data:
                        curs.execute(TEST_MAPPING_QUERY, (rdata[1], rdata[0]))
                        row = curs.fetchone()
                        if not row:
                            print("no match for '%s' '%s'" % (rdata[0], rdata[1]))
                            failed += 1
                            continue

                        if row[0] != int(rdata[2]):
                            mbid = get_mbid_for_release_id(mb_curs, int(row[0]))
                            print("'%s' '%s' expected %s, got %s (%s)" % (rdata[0], rdata[1], rdata[2], row[0], mbid))
                            failed += 1
                        else:
                            print("'%s' '%s' ok" % (rdata[0], rdata[1]))
                            passed += 1

    print("%d passed, %d failed." % (passed, failed))
