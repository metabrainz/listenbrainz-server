import sys

from listenbrainz_spark.mlhd.download import hdfs_upload
from listenbrainz_spark.mlhd.scripts import artist_popularity


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Please specify the MLHD script to call...")
        sys.exit(-1)

    if sys.argv[1] == 'hdfs_upload':
        try:
            path = sys.argv[2]
        except IndexError:
            print("No path to MLHD dump specified!")
            sys.exit(-1)
        hdfs_upload.main(path)
    elif sys.argv[1] == 'artist_popularity':
        artist_popularity.main()
