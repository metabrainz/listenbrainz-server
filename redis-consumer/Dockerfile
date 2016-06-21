FROM python:2.7.11

MAINTAINER Robert Kaye <rob@metabrainz.org>

# General setup
RUN apt-get update && apt-get install -y --no-install-recommends python-redis redis-tools

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

RUN mkdir /code
WORKDIR /code
COPY . /code
RUN pip install -r redis-consumer/requirements.txt
