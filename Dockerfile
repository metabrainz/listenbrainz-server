ARG PYTHON_BASE_IMAGE_VERSION=3.7-20210115
FROM metabrainz/python:$PYTHON_BASE_IMAGE_VERSION as listenbrainz-base

ARG PYTHON_BASE_IMAGE_VERSION

LABEL org.label-schema.vcs-url="https://github.com/metabrainz/listenbrainz-server.git" \
      org.label-schema.vcs-ref="" \
      org.label-schema.schema-version="1.0.0-rc1" \
      org.label-schema.vendor="MetaBrainz Foundation" \
      org.label-schema.name="ListenBrainz" \
      org.metabrainz.based-on-image="metabrainz/python:$PYTHON_BASE_IMAGE_VERSION"

# remove expired let's encrypt certificate and install new ones
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /usr/share/ca-certificates/mozilla/DST_Root_CA_X3.crt \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV DOCKERIZE_VERSION v0.6.1
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

ENV SENTRY_CLI_VERSION 1.63.1
RUN wget -O /usr/local/bin/sentry-cli https://downloads.sentry-cdn.com/sentry-cli/$SENTRY_CLI_VERSION/sentry-cli-Linux-x86_64 \
    && chmod +x /usr/local/bin/sentry-cli

ENV SENTRY_SERVICE_ERROR_ENVIRONMENT listenbrainz

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
                       build-essential \
                       git \
                       libffi-dev \
                       libpq-dev \
                       libssl-dev \
                       pxz \
                       redis-tools \
                       rsync \
                       uuid \
    && rm -rf /var/lib/apt/lists/*

# PostgreSQL client
RUN curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
ENV PG_MAJOR 12
RUN echo 'deb http://apt.postgresql.org/pub/repos/apt/ xenial-pgdg main' $PG_MAJOR > /etc/apt/sources.list.d/pgdg.list
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-$PG_MAJOR \
    && rm -rf /var/lib/apt/lists/*

# need to build librabbitmq
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        autoconf \
        automake \
        pkg-config \
        libtool \
    && rm -rf /var/lib/apt/lists/*

# While WORKDIR will create a directory if it doesn't already exist, we do it explicitly here
# so that we know what user it is created as: https://github.com/moby/moby/issues/36677
RUN mkdir -p /code/listenbrainz /static

WORKDIR /code/listenbrainz
RUN pip3 install pip==21.0.1
COPY requirements.txt /code/listenbrainz/
RUN pip3 install --no-cache-dir -r requirements.txt

# remove build dependencies
RUN apt remove -y autoconf \
        automake \
        pkg-config \
        libtool

############################################
# NOTE: The development image starts here. #
############################################
FROM listenbrainz-base as listenbrainz-dev
COPY requirements_development.txt /code/listenbrainz
RUN pip3 install --no-cache-dir -r requirements_development.txt
RUN mkdir /code/listenbrainz/docs
COPY ./docs/requirements.txt /code/listenbrainz/docs
RUN pip3 install --no-cache-dir -r ./docs/requirements.txt
COPY . /code/listenbrainz


###########################################
# NOTE: The production image starts here. #
###########################################
FROM listenbrainz-base as listenbrainz-prod

# Create directories for cron logs and dumps
# /mnt/dumps: Temporary working space for dumps
# /mnt/backup: All dumps
# /mnt/ftp: Subset of all dumps that are uploaded to
RUN mkdir /logs /mnt/dumps /mnt/backup /mnt/ftp

# Install NodeJS and front-end dependencies
RUN curl -sL https://deb.nodesource.com/setup_16.x | bash - && \
    apt-get install -y nodejs && rm -rf /var/lib/apt/lists/*
WORKDIR /static
COPY package.json package-lock.json /static/
RUN npm install


COPY ./docker/run-lb-command /usr/local/bin
COPY ./docker/lb-startup-common.sh /etc

# runit service files
# All services are created with a `down` file, preventing them from starting
# rc.local removes the down file for the specific service we want to run in a container
# http://smarden.org/runit/runsv.8.html

# cron
COPY ./docker/services/cron/consul-template-cron-config.conf /etc/consul-template-cron-config.conf
COPY ./docker/services/cron/cron-config.service /etc/service/cron-config/run
RUN touch /etc/service/cron/down
RUN touch /etc/service/cron-config/down

# API Compat (last.fm) server
COPY ./docker/services/api_compat/uwsgi-api-compat.ini /etc/uwsgi/uwsgi-api-compat.ini
COPY ./docker/services/api_compat/consul-template-api-compat.conf /etc/consul-template-api-compat.conf
COPY ./docker/services/api_compat/api_compat.service /etc/service/api_compat/run
COPY ./docker/services/api_compat/api_compat.finish /etc/service/api_compat/finish
RUN touch /etc/service/api_compat/down

# Websockets server
COPY ./docker/services/websockets/consul-template-websockets.conf /etc/consul-template-websockets.conf
COPY ./docker/services/websockets/websockets.service /etc/service/websockets/run
COPY ./docker/services/websockets/websockets.finish /etc/service/websockets/finish
RUN touch /etc/service/websockets/down

# Labs API
COPY ./docker/services/labs_api/uwsgi-labs-api.ini /etc/uwsgi/uwsgi-labs-api.ini
COPY ./docker/services/labs_api/consul-template-labs-api.conf /etc/consul-template-labs-api.conf
COPY ./docker/services/labs_api/labs_api.service /etc/service/labs_api/run
COPY ./docker/services/labs_api/labs_api.finish /etc/service/labs_api/finish
RUN touch /etc/service/labs_api/down

# Spark reader
COPY ./docker/services/spark_reader/consul-template-spark-reader.conf /etc/consul-template-spark-reader.conf
COPY ./docker/services/spark_reader/spark_reader.service /etc/service/spark_reader/run
COPY ./docker/services/spark_reader/spark_reader.finish /etc/service/spark_reader/finish
RUN touch /etc/service/spark_reader/down

# Spotify reader
COPY ./docker/services/spotify_reader/consul-template-spotify-reader.conf /etc/consul-template-spotify-reader.conf
COPY ./docker/services/spotify_reader/spotify_reader.service /etc/service/spotify_reader/run
COPY ./docker/services/spotify_reader/spotify_reader.finish /etc/service/spotify_reader/finish
RUN touch /etc/service/spotify_reader/down

# Timescale writer
COPY ./docker/services/timescale_writer/consul-template-timescale-writer.conf /etc/consul-template-timescale-writer.conf
COPY ./docker/services/timescale_writer/timescale_writer.service /etc/service/timescale_writer/run
COPY ./docker/services/timescale_writer/timescale_writer.finish /etc/service/timescale_writer/finish
RUN touch /etc/service/timescale_writer/down

# MBID-mapping writer
COPY ./docker/services/mbid_mapping_writer/consul-template-mbid-mapping-writer.conf /etc/consul-template-mbid-mapping-writer.conf
COPY ./docker/services/mbid_mapping_writer/mbid_mapping_writer.service /etc/service/mbid_mapping_writer/run
COPY ./docker/services/mbid_mapping_writer/mbid_mapping_writer.finish /etc/service/mbid_mapping_writer/finish
RUN touch /etc/service/mbid_mapping_writer/down

# uwsgi (website)
COPY ./docker/services/uwsgi/uwsgi.ini /etc/uwsgi/uwsgi.ini
COPY ./docker/services/uwsgi/consul-template-uwsgi.conf /etc/consul-template-uwsgi.conf
COPY ./docker/services/uwsgi/uwsgi.service /etc/service/uwsgi/run
COPY ./docker/services/uwsgi/uwsgi.finish /etc/service/uwsgi/finish
RUN touch /etc/service/uwsgi/down

COPY ./docker/rc.local /etc/rc.local

# crontab
COPY ./docker/services/cron/crontab /etc/cron.d/crontab
RUN chmod 0644 /etc/cron.d/crontab

# Compile front-end (static) files
COPY webpack.config.js babel.config.js .eslintrc.js tsconfig.json ./listenbrainz/webserver/static /static/
RUN npm run build:prod

# Now install our code, which may change frequently
COPY . /code/listenbrainz/

WORKDIR /code/listenbrainz
# Ensure we use the right files and folders by removing duplicates
RUN rm -rf ./listenbrainz/webserver/static/
RUN rm -f /code/listenbrainz/listenbrainz/config.py /code/listenbrainz/listenbrainz/config.pyc

ARG GIT_COMMIT_SHA
LABEL org.label-schema.vcs-ref=$GIT_COMMIT_SHA
ENV GIT_SHA ${GIT_COMMIT_SHA}
