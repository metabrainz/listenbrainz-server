import csv
import config

from mapping.search import search


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

            data.append(row)

    return data


def test_mapping():
    ''' This test will run as many test as there are in the CSV file, with the format"

        track_name,artist_credit_name,exected_MB_release_MBID
    '''

    data = _read_test_data("mapping/mapping_test/mapping_test_cases.csv")

    passed = 0
    failed = 0

    for row in data:
        hits = search(row[1] + " " + row[0])
        if not hits:
            failed += 1
            print("Q %-30s %-30s %-25s %s" % (row[0][:29], "", row[1][:29], row[2]))
            print("no results.")
            continue

        if row[2] != hits[0]['release_mbid']:
            print("Q %-30s %-30s %-25s %s" % (row[0][:29], "", row[1][:29], row[2]))
            print("H %-30s %-30s %-25s %s" % (hits[0]['recording_name'][:29], hits[0]['release_name'][:29],
                  hits[0]['artist_credit_name'][:29], hits[0]['release_mbid']))
            print()
            failed += 1
        else:
            passed += 1

    print("%d passed, %d failed." % (passed, failed))
