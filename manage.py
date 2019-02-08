import sys
from listenbrainz_spark.stats import user


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: manage.py <app_name>")
        sys.exit(-1)

    user.main(app_name=sys.argv[1])