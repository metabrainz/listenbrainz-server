FROM airdock/oracle-jdk:jdk-8u112

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    scala \
    wget

RUN cd /usr/local && \
    wget http://apache.rediris.es/spark/spark-2.3.0/spark-2.3.0-bin-hadoop2.7.tgz && \
    tar xzf spark-2.3.0-bin-hadoop2.7.tgz && \
    ln -s spark-2.3.0-bin-hadoop2.7 spark

RUN mkdir /rec
WORKDIR /rec
COPY . /rec

CMD /rec/docker/worker-entry-script.py
