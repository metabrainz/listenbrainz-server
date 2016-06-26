FROM python:2.7.11

MAINTAINER Robert Kaye <rob@metabrainz.org>

# General setup
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    git \
    redis-tools \ 
    wget 
RUN mkdir /code

# PostgreSQL client
RUN apt-key adv --keyserver ha.pool.sks-keyservers.net --recv-keys B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8
ENV PG_MAJOR 9.5
ENV PG_VERSION 9.5.3-1.pgdg80+1
RUN echo 'deb http://apt.postgresql.org/pub/repos/apt/ jessie-pgdg main' $PG_MAJOR > /etc/apt/sources.list.d/pgdg.list
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-$PG_MAJOR=$PG_VERSION \
    && rm -rf /var/lib/apt/lists/*
# Specifying password so that client doesn't ask scripts for it...
ENV PGPASSWORD "listenbrainz"

# MessyBrainz
WORKDIR /code
RUN git clone https://github.com/metabrainz/messybrainz-server.git

WORKDIR /code/messybrainz-server
RUN pip install -r requirements.txt
RUN python setup.py install

# ListenBrainz
RUN mkdir /code/listenbrainz
WORKDIR /code/listenbrainz

# These following steps are redundant, but they prevent the requirements from being installed too many times
COPY requirements.txt /code/listenbrainz/
RUN pip install -r requirements.txt

# Now install our code, which may change frequently
COPY . /code/listenbrainz/
