FROM metabrainz/python:3.7 as listenbrainz-base

ARG deploy_env

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
RUN pip3 install -U pip
COPY requirements.txt /code/listenbrainz/
RUN pip3 install --no-cache-dir -r requirements.txt
RUN useradd --create-home --shell /bin/bash listenbrainz


############################################
# NOTE: The development image starts here. #
############################################
FROM listenbrainz-base as listenbrainz-dev
ARG deploy_env
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
ARG deploy_env


# production sidenote: We create a `lbdumps` user to create data dumps because
# the ListenBrainz servers on prod (etc. lemmy) use storage boxes [0] which
# are owned by lbdumps on the host too.
# [0]: https://github.com/metabrainz/syswiki/blob/master/ListenBrainzStorageBox.md
RUN groupadd --gid 900 lbdumps
RUN useradd --create-home --shell /bin/bash --uid 900 --gid 900 lbdumps

RUN groupadd --gid 901 listenbrainz_stats_cron
RUN useradd --create-home --shell /bin/bash --uid 901 --gid 901 listenbrainz_stats_cron


# Add cron jobs
ADD docker/stats-crontab /etc/cron.d/stats-crontab
RUN chmod 0644 /etc/cron.d/stats-crontab && crontab -u listenbrainz_stats_cron /etc/cron.d/stats-crontab
ADD docker/dump-crontab /etc/cron.d/dump-crontab
RUN chmod 0644 /etc/cron.d/dump-crontab && crontab -u lbdumps /etc/cron.d/dump-crontab

# Make sure the cron service doesn't start automagically
# http://smarden.org/runit/runsv.8.html
RUN touch /etc/service/cron/down

# Consul Template service is already set up with the base image.
# Just need to copy the configuration.
COPY ./docker/consul-template.conf /etc/consul-template.conf
COPY ./docker/$deploy_env/uwsgi/uwsgi.service /etc/service/uwsgi/run
RUN chmod 755 /etc/service/uwsgi/run
COPY ./docker/$deploy_env/uwsgi/uwsgi.ini /etc/uwsgi/uwsgi.ini
COPY ./docker/$deploy_env/uwsgi/uwsgi-labs-api.ini /etc/uwsgi/uwsgi-labs-api.ini
COPY ./docker/prod/uwsgi/uwsgi-api-compat.ini /etc/uwsgi/uwsgi-api-compat.ini
RUN touch /etc/service/uwsgi/down

COPY ./docker/rc.local /etc/rc.local

# Create directories for backups and FTP syncs
RUN mkdir /home/lbdumps/backup /home/lbdumps/ftp
RUN chown -R lbdumps:lbdumps /home/lbdumps/backup /home/lbdumps/ftp

RUN mkdir /static
WORKDIR /static

# Compile static files
RUN curl -sL https://deb.nodesource.com/setup_10.x | bash - && \
    apt-get install -y nodejs && rm -rf /var/lib/apt/lists/*
COPY package.json package-lock.json webpack.config.js ./listenbrainz/webserver/static /static/
RUN npm install && npm run build:prod && ./node_modules/less/bin/lessc --clean-css /static/css/main.less > /static/css/main.css && \
    rm -rf node_modules js/*.jsx *.json webpack.config.js && npm cache clean --force

# Now install our code, which may change frequently
COPY . /code/listenbrainz/

WORKDIR /code/listenbrainz
RUN rm -rf ./listenbrainz/webserver/static/
RUN rm -f /code/listenbrainz/listenbrainz/config.py /code/listenbrainz/listenbrainz/config.pyc
