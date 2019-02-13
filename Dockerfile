FROM airdock/oraclejdk:1.8

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    scala \
    wget \
    net-tools \
    bsdmainutils 

ENV DOCKERIZE_VERSION v0.6.1
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && rm dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

COPY docker/apache-download.sh /apache-download.sh
RUN cd /usr/local && \
    /apache-download.sh spark/spark-2.3.1/spark-2.3.1-bin-hadoop2.7.tgz && \
    tar xzf spark-2.3.1-bin-hadoop2.7.tgz && \
    ln -s spark-2.3.1-bin-hadoop2.7 spark
