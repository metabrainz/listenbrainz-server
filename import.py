import sys
from listenbrainz_spark.data import import_dump 

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: import.py <app_name> <dump_file>")
        sys.exit(-1)

    import_dump.main(app_name=sys.argv[1], archive=sys.argv[2])
