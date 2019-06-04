FROM airdock/oraclejdk:1.8 as metabrainz-spark-base

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    scala \
    wget \
    net-tools \
    dnsutils \
    python3-dev \
    python3-pip \
    python3-numpy \
    bsdmainutils \
    xz-utils \
    pxz \
    zip

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 10

RUN mkdir /rec
WORKDIR /rec
COPY requirements.txt /rec/requirements.txt
RUN pip3 install -r requirements.txt


ENV DOCKERIZE_VERSION v0.6.1
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && rm dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

COPY docker/apache-download.sh /apache-download.sh
ENV SPARK_VERSION 2.3.1
ENV HADOOP_VERSION 2.7
RUN cd /usr/local && \
    /apache-download.sh spark/spark-$SPARK_VERSION/spark-$SPARK_VERSION-bin-hadoop$HADOOP_VERSION.tgz && \
    tar xzf spark-$SPARK_VERSION-bin-hadoop$HADOOP_VERSION.tgz && \
    ln -s spark-$SPARK_VERSION-bin-hadoop$HADOOP_VERSION spark


FROM metabrainz-spark-base as metabrainz-spark-master
CMD /usr/local/spark/sbin/start-master.sh

FROM metabrainz-spark-base as metabrainz-spark-worker
CMD dockerize -wait tcp://spark-master:7077 -timeout 9999s /usr/local/spark/sbin/start-slave.sh spark://spark-master:7077

FROM metabrainz-spark-base as metabrainz-spark-jobs
COPY . /rec

FROM metabrainz-spark-base as metabrainz-spark-dev
COPY . /rec
