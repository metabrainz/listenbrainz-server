FROM python:2.7.11

MAINTAINER Robert Kaye <rob@metabrainz.org>

# General setup
RUN apt-get update && apt-get install -y build-essential git wget

RUN mkdir /code
ENV DOCKERIZE_VERSION v0.2.0
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
            && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

# PostgreSQL client
RUN apt-key adv --keyserver ha.pool.sks-keyservers.net --recv-keys B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8
ENV PG_MAJOR 9.5
ENV PG_VERSION 9.5.3-1.pgdg80+1
RUN echo 'deb http://apt.postgresql.org/pub/repos/apt/ jessie-pgdg main' $PG_MAJOR > /etc/apt/sources.list.d/pgdg.list
RUN apt-get update \
    && apt-get install -y postgresql-client-$PG_MAJOR=$PG_VERSION \
    && rm -rf /var/lib/apt/lists/*
# Specifying password so that client doesn't ask scripts for it...
ENV PGPASSWORD "listenbrainz"

# MessyBrainz
WORKDIR /code
RUN git clone https://github.com/metabrainz/messybrainz-server.git

WORKDIR /code/messybrainz-server
ADD messybrainz-config.py.docker /code/messybrainz-server/config.py
RUN pip install -r requirements.txt
RUN python setup.py install

# ListenBrainz
RUN mkdir /code/listenbrainz
WORKDIR /code/listenbrainz
ADD requirements.txt /code/listenbrainz/
RUN pip install -r requirements.txt
ADD . /code/listenbrainz/
ADD config.py.docker /code/listenbrainz/config.py
