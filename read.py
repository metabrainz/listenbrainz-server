import sys
from listenbrainz_spark import sqlContext

if __name__ == '__main__':
    df = sqlContext.read.parquet('hdfs://hadoop-master.spark-network:9000/data/listenbrainz/2017/12.parquet')
    print(df.count())
