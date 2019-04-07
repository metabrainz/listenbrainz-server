import sys
from listenbrainz_spark.mlhd.setup import hdfs_upload 

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: load_mlhd  <app_name> <directory>")
        sys.exit(-1)

    hdfs_upload.main(sys.argv[2])
