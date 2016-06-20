FROM python:2.7.11

MAINTAINER Robert Kaye <rob@metabrainz.org>

# General setup
RUN apt-get update && apt-get install -y build-essential git
RUN mkdir /code

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
#RUN git checkout docker
#RUN cp /code/messybrainz-sever/config.py.docker /code/messybrainz/config.py
ADD messybrainz-config.py.docker /code/messybrainz-server/config.py
RUN pip install -r requirements.txt
RUN python setup.py install
#RUN python manage.py init_db

# ListenBrainz
RUN mkdir /code/listenbrainz
WORKDIR /code/listenbrainz
ADD requirements.txt /code/listenbrainz/
RUN pip install -r requirements.txt
ADD config.py.docker /code/listenbrainz/config.py
#RUN python manage.py init_db
ADD . /code/listenbrainz/

EXPOSE 8080
CMD ./server.py
