FROM python:2.7.12

ENV DOCKERIZE_VERSION v0.2.0
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
                       build-essential \
                       redis-tools \
                       git \
    && rm -rf /var/lib/apt/lists/*

# PostgreSQL client
RUN apt-key adv --keyserver ha.pool.sks-keyservers.net --recv-keys B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8
ENV PG_MAJOR 9.5
ENV PG_VERSION 9.5.5-1.pgdg80+1
RUN echo 'deb http://apt.postgresql.org/pub/repos/apt/ jessie-pgdg main' $PG_MAJOR > /etc/apt/sources.list.d/pgdg.list
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-$PG_MAJOR=$PG_VERSION \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /code
WORKDIR /code

# MessyBrainz
RUN git clone https://github.com/metabrainz/messybrainz-server.git messybrainz
WORKDIR /code/messybrainz
RUN pip install -r requirements.txt
RUN python setup.py install

RUN mkdir /code/listenbrainz
WORKDIR /code/listenbrainz

COPY requirements.txt /code/listenbrainz/
RUN pip install -r requirements.txt

COPY . /code/listenbrainz/

CMD python manage.py runserver -h 0.0.0.0 -p 80 -d
