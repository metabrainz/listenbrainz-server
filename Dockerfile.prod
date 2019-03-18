FROM metabrainz/python:3.7

ARG deploy_env

ENV DOCKERIZE_VERSION v0.6.1
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
                       build-essential \
                       git \
                       libpq-dev \
                       libffi-dev \
                       libssl-dev \
                       redis-tools \
                       pxz \
                       rsync \
    && rm -rf /var/lib/apt/lists/*


# PostgreSQL client
RUN apt-key adv --keyserver ha.pool.sks-keyservers.net --recv-keys B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8
ENV PG_MAJOR 9.5
RUN echo 'deb http://apt.postgresql.org/pub/repos/apt/ jessie-pgdg main' $PG_MAJOR > /etc/apt/sources.list.d/pgdg.list
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-$PG_MAJOR \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install uWSGI==2.0.18

RUN mkdir /code
WORKDIR /code

# MessyBrainz
RUN git clone https://github.com/metabrainz/messybrainz-server.git messybrainz
WORKDIR /code/messybrainz
RUN git checkout production
RUN pip3 install -r requirements.txt
RUN python3 setup.py install

# ListenBrainz
WORKDIR /code/listenbrainz
COPY ./requirements.txt .
RUN pip3 install -r requirements.txt

# Node
RUN curl -sL https://deb.nodesource.com/setup_10.x | bash - && \
    apt-get install -y nodejs && rm -rf /var/lib/apt/lists/*
RUN mkdir /static
WORKDIR /static
COPY package.json package-lock.json webpack.config.js ./listenbrainz/webserver/static /static/
RUN npm install && npm run build:prod && ./node_modules/less/bin/lessc --clean-css /static/css/main.less > /static/css/main.css && \
    rm -rf node_modules js/*.jsx *.json webpack.config.js && npm cache clean --force

COPY . /code/listenbrainz
WORKDIR /code/listenbrainz
RUN rm -rf ./listenbrainz/webserver/static/


# Sometimes the local copy of config.py[c] gets in the way. Better nuke it to not conflict.
RUN rm -f /code/listenbrainz/listenbrainz/config.py /code/listenbrainz/listenbrainz/config.pyc

# create a user named listenbrainz for cron jobs and storing dump file backups
RUN useradd --create-home --shell /bin/bash listenbrainz
RUN mkdir /home/listenbrainz/backup /home/listenbrainz/ftp
RUN chown -R listenbrainz:listenbrainz /home/listenbrainz/backup /home/listenbrainz/ftp

# Add cron jobs
ADD docker/crontab /etc/cron.d/lb-crontab
RUN chmod 0644 /etc/cron.d/lb-crontab && crontab -u listenbrainz /etc/cron.d/lb-crontab
RUN touch /var/log/stats.log /var/log/dump_create.log && chown listenbrainz:listenbrainz /var/log/stats.log /var/log/dump_create.log

# Make sure the cron service doesn't start automagically
# http://smarden.org/runit/runsv.8.html
RUN touch /etc/service/cron/down

# Consul Template service is already set up with the base image.
# Just need to copy the configuration.
COPY ./docker/consul-template.conf /etc/consul-template.conf

COPY ./docker/$deploy_env/uwsgi/uwsgi.service /etc/service/uwsgi/run
RUN chmod 755 /etc/service/uwsgi/run
COPY ./docker/$deploy_env/uwsgi/uwsgi.ini /etc/uwsgi/uwsgi.ini
COPY ./docker/prod/uwsgi/uwsgi-api-compat.ini /etc/uwsgi/uwsgi-api-compat.ini

# setup a log dir
RUN mkdir /logs
RUN chown -R daemon:daemon /logs
