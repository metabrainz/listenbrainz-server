ARG PYTHON_BASE_IMAGE_VERSION=3.11-20231006
ARG NODE_VERSION=20-alpine
FROM metabrainz/python:$PYTHON_BASE_IMAGE_VERSION as listenbrainz-base

ARG PYTHON_BASE_IMAGE_VERSION

LABEL org.label-schema.vcs-url="https://github.com/metabrainz/listenbrainz-server.git" \
      org.label-schema.vcs-ref="" \
      org.label-schema.schema-version="1.0.0-rc1" \
      org.label-schema.vendor="MetaBrainz Foundation" \
      org.label-schema.name="ListenBrainz" \
      org.metabrainz.based-on-image="metabrainz/python:$PYTHON_BASE_IMAGE_VERSION"

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
                       xz-utils \
                       redis-tools \
                       rsync \
                       uuid \
                       zstd \
    && rm -rf /var/lib/apt/lists/*

# PostgreSQL client
RUN curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
ENV PG_MAJOR 12
RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" $PG_MAJOR > /etc/apt/sources.list.d/pgdg.list
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-$PG_MAJOR \
    && rm -rf /var/lib/apt/lists/*

# While WORKDIR will create a directory if it doesn't already exist, we do it explicitly here
# so that we know what user it is created as: https://github.com/moby/moby/issues/36677
RUN mkdir -p /code/listenbrainz /static

WORKDIR /code/listenbrainz
COPY requirements.txt /code/listenbrainz/
RUN pip3 install --no-cache-dir -r requirements.txt


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


#####################################################################################################
# NOTE: The javascript files are continously watched and compiled using this image in developement. #
#####################################################################################################
FROM node:$NODE_VERSION as listenbrainz-frontend-dev

ARG NODE_VERSION

LABEL org.label-schema.vcs-url="https://github.com/metabrainz/listenbrainz-server.git" \
      org.label-schema.schema-version="1.0.0-rc1" \
      org.label-schema.vendor="MetaBrainz Foundation" \
      org.label-schema.name="ListenBrainz Static Builder" \
      org.metabrainz.based-on-image="node:$NODE_VERSION"

RUN mkdir /code
WORKDIR /code

COPY package.json package-lock.json /code/
RUN npm install

COPY webpack.config.js babel.config.js enzyme.config.ts jest.config.js tsconfig.json .eslintrc.js .stylelintrc.js /code/


#########################################################################
# NOTE: The javascript files for production are compiled in this image. #
#########################################################################
FROM listenbrainz-frontend-dev as listenbrainz-frontend-prod

# Compile front-end (static) files
COPY ./frontend /code/frontend
RUN npm run build:prod


###########################################
# NOTE: The production image starts here. #
###########################################
FROM listenbrainz-base as listenbrainz-prod

# Create directories for cron logs and dumps
# /mnt/dumps: Temporary working space for dumps
# /mnt/backup: All dumps
# /mnt/ftp: Subset of all dumps that are uploaded to
RUN mkdir /logs /mnt/dumps /mnt/backup /mnt/ftp

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

# Spotify Metadata Cache
COPY ./docker/services/spotify_metadata_cache/consul-template-spotify-metadata-cache.conf /etc/consul-template-spotify-metadata-cache.conf
COPY ./docker/services/spotify_metadata_cache/spotify_metadata_cache.service /etc/service/spotify_metadata_cache/run
COPY ./docker/services/spotify_metadata_cache/spotify_metadata_cache.finish /etc/service/spotify_metadata_cache/finish
RUN touch /etc/service/spotify_metadata_cache/down

# Apple Metadata Cache
COPY ./docker/services/apple_metadata_cache/consul-template-apple-metadata-cache.conf /etc/consul-template-apple-metadata-cache.conf
COPY ./docker/services/apple_metadata_cache/apple_metadata_cache.service /etc/service/apple_metadata_cache/run
COPY ./docker/services/apple_metadata_cache/apple_metadata_cache.finish /etc/service/apple_metadata_cache/finish
RUN touch /etc/service/apple_metadata_cache/down

# uwsgi (website)
COPY ./docker/services/uwsgi/uwsgi.ini.ctmpl /etc/uwsgi/uwsgi.ini.ctmpl
COPY ./docker/services/uwsgi/consul-template-uwsgi.conf /etc/consul-template-uwsgi.conf
COPY ./docker/services/uwsgi/uwsgi.service /etc/service/uwsgi/run
COPY ./docker/services/uwsgi/uwsgi.finish /etc/service/uwsgi/finish
RUN touch /etc/service/uwsgi/down

COPY ./docker/rc.local /etc/rc.local

# crontab
COPY ./docker/services/cron/crontab /etc/cron.d/crontab
RUN chmod 0644 /etc/cron.d/crontab

# copy the compiled js files and statis assets from image to prod
COPY --from=listenbrainz-frontend-prod /code/frontend/robots.txt /static/
COPY --from=listenbrainz-frontend-prod /code/frontend/sound /static/sound
COPY --from=listenbrainz-frontend-prod /code/frontend/fonts /static/fonts
COPY --from=listenbrainz-frontend-prod /code/frontend/img /static/img
COPY --from=listenbrainz-frontend-prod /code/frontend/js/lib /static/js/lib
COPY --from=listenbrainz-frontend-prod /code/frontend/dist /static/dist

# Now install our code, which may change frequently
COPY . /code/listenbrainz/

WORKDIR /code/listenbrainz
# Ensure we use the right files and folders by removing duplicates
RUN rm -rf ./frontend/
RUN rm -f /code/listenbrainz/listenbrainz/config.py /code/listenbrainz/listenbrainz/config.pyc

ARG GIT_COMMIT_SHA
LABEL org.label-schema.vcs-ref=$GIT_COMMIT_SHA
ENV GIT_SHA ${GIT_COMMIT_SHA}
