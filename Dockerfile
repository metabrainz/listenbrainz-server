ARG PYTHON_BASE_IMAGE_VERSION=3.7-20210115
FROM metabrainz/python:$PYTHON_BASE_IMAGE_VERSION as listenbrainz-base

ARG deploy_env
ARG GIT_COMMIT_SHA

LABEL org.label-schema.vcs-url="https://github.com/metabrainz/listenbrainz-server.git" \
      org.label-schema.vcs-ref=$GIT_COMMIT_SHA \
      org.label-schema.schema-version="1.0.0-rc1" \
      org.label-schema.vendor="MetaBrainz Foundation" \
      org.label-schema.name="ListenBrainz" \
      org.metabrainz.based-on-image="metabrainz/python:$PYTHON_BASE_IMAGE_VERSION"


ENV DOCKERIZE_VERSION v0.6.1
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

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
    && rm -rf /var/lib/apt/lists/*

# PostgreSQL client
RUN curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
ENV PG_MAJOR 12
RUN echo 'deb http://apt.postgresql.org/pub/repos/apt/ jessie-pgdg main' $PG_MAJOR > /etc/apt/sources.list.d/pgdg.list
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-$PG_MAJOR \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /code
WORKDIR /code

RUN mkdir /code/listenbrainz
WORKDIR /code/listenbrainz
RUN pip3 install pip==21.0.1
COPY requirements.txt /code/listenbrainz/
RUN pip3 install --no-cache-dir -r requirements.txt
RUN useradd --create-home --shell /bin/bash listenbrainz


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


# production sidenote: We create a `lbdumps` user to create data dumps because
# the ListenBrainz servers on prod (etc. lemmy) use storage boxes [0] which
# are owned by lbdumps on the host too.
# [0]: https://github.com/metabrainz/syswiki/blob/master/ListenBrainzStorageBox.md
RUN groupadd --gid 900 lbdumps
RUN useradd --create-home --shell /bin/bash --uid 900 --gid 900 lbdumps

RUN groupadd --gid 901 listenbrainz_stats_cron
RUN useradd --create-home --shell /bin/bash --uid 901 --gid 901 listenbrainz_stats_cron
RUN mkdir /logs && chown lbdumps:lbdumps /logs

# Create directories for backups and FTP syncs
RUN mkdir /home/lbdumps/backup /home/lbdumps/ftp
RUN chown -R lbdumps:lbdumps /home/lbdumps/backup /home/lbdumps/ftp

# Install NodeJS and front-end dependencies
RUN mkdir /static
RUN curl -sL https://deb.nodesource.com/setup_10.x | bash - && \
    apt-get install -y nodejs && rm -rf /var/lib/apt/lists/*
COPY package.json package-lock.json /static/
WORKDIR /static
RUN npm install

# runit service files
# All services are created with a `down` file, preventing them from starting
# rc.local removes the down file for the specific service we want to run in a container
# http://smarden.org/runit/runsv.8.html

COPY ./docker/run-lb-command /usr/local/bin

# cron
COPY ./docker/services/cron/consul-template-cron-config.conf /etc/consul-template-cron-config.conf
COPY ./docker/services/cron/cron-config.service /etc/service/cron-config/run
RUN touch /etc/service/cron/down
RUN touch /etc/service/cron-config/down

# API Compat (last.fm) server
COPY ./docker/services/api_compat/uwsgi-api-compat.ini /etc/uwsgi/uwsgi-api-compat.ini
COPY ./docker/services/api_compat/consul-template-api-compat.conf /etc/consul-template-api-compat.conf
COPY ./docker/services/api_compat/api_compat.service /etc/service/api_compat/run
RUN touch /etc/service/api_compat/down

# Websockets server
COPY ./docker/services/websockets/consul-template-websockets.conf /etc/consul-template-websockets.conf
COPY ./docker/services/websockets/websockets.service /etc/service/websockets/run
RUN touch /etc/service/websockets/down

# Labs API
COPY ./docker/services/labs_api/uwsgi-labs-api.ini /etc/uwsgi/uwsgi-labs-api.ini
COPY ./docker/services/labs_api/consul-template-labs-api.conf /etc/consul-template-labs-api.conf
COPY ./docker/services/labs_api/labs_api.service /etc/service/labs_api/run
RUN touch /etc/service/labs_api/down

# Spark reader
COPY ./docker/services/spark_reader/consul-template-spark-reader.conf /etc/consul-template-spark-reader.conf
COPY ./docker/services/spark_reader/spark_reader.service /etc/service/spark_reader/run
RUN touch /etc/service/spark_reader/down

# Spotify reader
COPY ./docker/services/spotify_reader/consul-template-spotify-reader.conf /etc/consul-template-spotify-reader.conf
COPY ./docker/services/spotify_reader/spotify_reader.service /etc/service/spotify_reader/run
RUN touch /etc/service/spotify_reader/down

# Timescale writer
COPY ./docker/services/timescale_writer/consul-template-timescale-writer.conf /etc/consul-template-timescale-writer.conf
COPY ./docker/services/timescale_writer/timescale_writer.service /etc/service/timescale_writer/run
RUN touch /etc/service/timescale_writer/down

# uwsgi (website)
COPY ./docker/services/uwsgi/uwsgi.ini /etc/uwsgi/uwsgi.ini
COPY ./docker/services/uwsgi/consul-template-uwsgi.conf /etc/consul-template-uwsgi.conf
COPY ./docker/services/uwsgi/uwsgi.service /etc/service/uwsgi/run
RUN touch /etc/service/uwsgi/down

COPY ./docker/rc.local /etc/rc.local

# crontabs
COPY ./docker/services/cron/stats-crontab /etc/cron.d/stats-crontab
RUN chmod 0644 /etc/cron.d/stats-crontab
COPY ./docker/services/cron/dump-crontab /etc/cron.d/dump-crontab
RUN chmod 0644 /etc/cron.d/dump-crontab

# Compile front-end (static) files
COPY webpack.config.js .eslintrc.js tsconfig.json ./listenbrainz/webserver/static /static/
RUN npm run build:prod

# Now install our code, which may change frequently
COPY . /code/listenbrainz/

WORKDIR /code/listenbrainz
# Ensure we use the right files and folders by removing duplicates
RUN rm -rf ./listenbrainz/webserver/static/
RUN rm -f /code/listenbrainz/listenbrainz/config.py /code/listenbrainz/listenbrainz/config.pyc

ARG GIT_COMMIT_SHA
ENV GIT_SHA ${GIT_COMMIT_SHA}
